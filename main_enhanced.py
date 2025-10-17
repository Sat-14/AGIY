import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from tools import all_tools
from datetime import datetime
import uuid

# Import MongoDB and monitoring modules
from database.mongodb_config import get_db_manager
from monitoring.tracing import TracingManager, trace_function
from monitoring.metrics import MetricsManager
from monitoring.logging_config import (
    StructuredLogger,
    log_business_event,
    log_error
)

# Load environment variables
load_dotenv()

# Initialize monitoring
tracing = TracingManager("sales-agent", "1.0.0")
metrics = MetricsManager("sales-agent")
logging_config = StructuredLogger("sales-agent")
logger = logging_config.get_logger()

# Initialize MongoDB
db_manager = get_db_manager()
conversations_collection = db_manager.get_collection("conversations")
user_profiles_collection = db_manager.get_collection("user_profiles")


class ConversationManager:
    """Manages conversation persistence with MongoDB"""

    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    @trace_function
    def load_conversation_history(self):
        """Load previous conversation from MongoDB"""
        try:
            with tracing.create_span("load_conversation_history") as span:
                span.set_attribute("user_id", self.user_id)

                # Find most recent active conversation
                conversation = conversations_collection.find_one(
                    {"user_id": self.user_id, "active": True},
                    sort=[("timestamp", -1)]
                )

                if conversation:
                    logger.info(f"Loading conversation history for user {self.user_id}")

                    # Restore messages to memory
                    for msg in conversation.get("messages", []):
                        if msg["role"] == "human":
                            self.memory.chat_memory.add_message(
                                HumanMessage(content=msg["content"])
                            )
                        elif msg["role"] == "ai":
                            self.memory.chat_memory.add_message(
                                AIMessage(content=msg["content"])
                            )

                    self.session_id = conversation["session_id"]
                    log_business_event(
                        logger,
                        "conversation_resumed",
                        user_id=self.user_id,
                        details={"session_id": self.session_id}
                    )
                    return True

                logger.info(f"No previous conversation found for user {self.user_id}")
                return False

        except Exception as e:
            log_error(logger, e, {"operation": "load_conversation_history"})
            metrics.record_error("conversation_load_error")
            return False

    @trace_function
    def save_message(self, role, content):
        """Save individual message to MongoDB"""
        try:
            with tracing.create_span("save_message") as span:
                span.set_attribute("role", role)

                message_doc = {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.utcnow(),
                    "metadata": {}
                }

                # Update or insert conversation
                conversations_collection.update_one(
                    {"session_id": self.session_id},
                    {
                        "$set": {
                            "user_id": self.user_id,
                            "timestamp": datetime.utcnow(),
                            "active": True
                        },
                        "$push": {"messages": message_doc}
                    },
                    upsert=True
                )

                metrics.active_sessions.set(
                    conversations_collection.count_documents({"active": True})
                )

        except Exception as e:
            log_error(logger, e, {"operation": "save_message"})
            metrics.record_error("message_save_error")

    @trace_function
    def close_session(self):
        """Mark session as inactive"""
        try:
            conversations_collection.update_one(
                {"session_id": self.session_id},
                {"$set": {"active": False}}
            )
            log_business_event(
                logger,
                "conversation_ended",
                user_id=self.user_id,
                details={"session_id": self.session_id}
            )
        except Exception as e:
            log_error(logger, e, {"operation": "close_session"})


class UserProfileManager:
    """Manages user profile data in MongoDB"""

    @staticmethod
    @trace_function
    def get_or_create_profile(user_id):
        """Get user profile or create default"""
        try:
            profile = user_profiles_collection.find_one({"user_id": user_id})

            if not profile:
                # Create default profile
                profile = {
                    "user_id": user_id,
                    "preferences": ["casual"],
                    "size": "M",
                    "purchase_history": [],
                    "browsing_history": [],
                    "loyalty_tier": "silver",
                    "loyalty_points": 500,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                user_profiles_collection.insert_one(profile)
                logger.info(f"Created new profile for user {user_id}")

            return profile

        except Exception as e:
            log_error(logger, e, {"operation": "get_or_create_profile"})
            return None

    @staticmethod
    @trace_function
    def update_browsing_history(user_id, item):
        """Update user browsing history"""
        try:
            user_profiles_collection.update_one(
                {"user_id": user_id},
                {
                    "$push": {"browsing_history": item},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        except Exception as e:
            log_error(logger, e, {"operation": "update_browsing_history"})


# Setup LLM
llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0)

# Define Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are Ria, a friendly and knowledgeable fashion expert and personal stylist for ABFRL.

🎯 YOUR ROLE - CONSULTATIVE SALES EXPERT:
You combine fashion expertise with consultative selling to create exceptional customer experiences.

📋 SALES PSYCHOLOGY TECHNIQUES:
1. ASK OPEN-ENDED QUESTIONS:
   - "What occasion are you shopping for?"
   - "What's your preferred style - casual, formal, or something in between?"
   - "What colors do you typically gravitate towards?"
   - "How would you describe your personal style?"

2. UNDERSTAND CUSTOMER NEEDS:
   - Listen actively to their requirements
   - Identify unstated needs (e.g., if they mention a wedding, suggest complete outfits)
   - Probe for budget, timeline, and preferences

3. SUGGEST COMPLEMENTARY ITEMS:
   - "These shoes pair beautifully with that jacket!"
   - "Have you considered adding a belt to complete the look?"
   - "This scarf would add a perfect finishing touch"
   - Always explain WHY items work together

4. HANDLE OBJECTIONS GRACEFULLY:
   - Price concerns: Highlight value, quality, and available offers/loyalty points
   - Stock issues: Suggest similar alternatives immediately
   - Style doubts: Provide styling tips and reassurance
   - Payment failures: Offer alternative payment methods calmly

5. CREATE URGENCY (ETHICALLY):
   - "This is one of our bestsellers and stock is running low"
   - "I see we only have a few left in your size at this location"
   - "There's a special offer available right now that could save you ₹X"

🛍️ OMNICHANNEL CONSISTENCY:
- Maintain conversation context if customer switches channels (chat → in-store)
- Reference previous interactions: "I remember you were looking at that blue jacket earlier"
- Session continuity is KEY - always use conversation history

🔧 TOOL USAGE - SMART ORCHESTRATION:
- Check inventory BEFORE suggesting specific items
- Show offers/loyalty points proactively during checkout discussions
- Track orders when customers ask about delivery
- Handle returns with empathy

⚠️ EDGE CASE HANDLING:
1. OUT OF STOCK: "I see that item is currently out of stock. Let me suggest similar alternatives that match your style..."
2. PAYMENT FAILURE: "It looks like the payment didn't go through. Would you like to try a different payment method or use your loyalty points?"
3. LOW STOCK: "Great choice! I should mention we only have X items left in stock at your preferred location."
4. UNAVAILABLE SIZE/COLOR: "That color/size is currently unavailable, but we have [alternatives]. Would you like to see them?"

💡 BEST PRACTICES:
- Be conversational and warm, not robotic
- Use customer's name if known
- Celebrate their choices: "Excellent choice! That's a customer favorite"
- Bundle intelligently: Suggest complete outfits, not random items
- Always close with a clear next step

Remember: You're not just selling products—you're helping customers look and feel their best!"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


def main():
    """Main conversation loop with MongoDB persistence"""

    # Get current user (in production, this comes from authentication)
    current_user_id = os.getenv("USER_ID", "user_12345")

    # Initialize conversation manager
    conv_manager = ConversationManager(current_user_id)

    # Load user profile
    user_profile = UserProfileManager.get_or_create_profile(current_user_id)

    # Load previous conversation if exists
    has_history = conv_manager.load_conversation_history()
    if has_history:
        print("--- Welcome back! Loading your previous conversation. ---")
    else:
        print("--- Starting a new conversation. ---")

    # Create agent
    agent = create_tool_calling_agent(llm, all_tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=all_tools,
        verbose=True,
        memory=conv_manager.memory
    )

    # Greeting
    print(f"Hello! I'm Ria. Your user ID is {current_user_id}.")
    if user_profile:
        print(f"Loyalty Tier: {user_profile.get('loyalty_tier', 'N/A').upper()} | Points: {user_profile.get('loyalty_points', 0)}")
    print("How can I help you today?\n")

    # Conversation loop
    while True:
        try:
            user_input = input("You: ")

            if user_input.lower() in ["exit", "quit"]:
                conv_manager.close_session()
                print("Goodbye! Your conversation has been saved.")
                break

            # Save user message
            conv_manager.save_message("human", user_input)

            # Track request
            start_time = datetime.utcnow()

            # Execute agent
            with tracing.create_span("agent_execution") as span:
                span.set_attribute("user_id", current_user_id)

                result = agent_executor.invoke({"input": user_input})
                response = result['output']

                # Save AI response
                conv_manager.save_message("ai", response)

                # Record metrics
                duration = (datetime.utcnow() - start_time).total_seconds()
                metrics.record_request("CLI", "agent_invoke", 200, duration)

                print(f"Ria: {response}\n")

                log_business_event(
                    logger,
                    "message_exchanged",
                    user_id=current_user_id,
                    details={
                        "session_id": conv_manager.session_id,
                        "duration": duration
                    }
                )

        except Exception as e:
            print("\nRia: I'm sorry, I've encountered a technical issue. Please try your request again shortly.\n")
            log_error(logger, e, {"user_id": current_user_id})
            metrics.record_error(type(e).__name__)


if __name__ == "__main__":
    main()
