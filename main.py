import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from tools import all_tools

# Load environment variables from .env file
load_dotenv()

# --- Part 2: Simulate a User Database / CRM ---
# In a real application, this would be a database (like Redis or a SQL DB).
# For our prototype, a simple dictionary will work to store session histories.
user_sessions = {}
# Let's assign a user ID for this session. In a real app, this would come from a login system.
current_user_id = "user_12345" 
# --- End of Part 2 ---

# 1. Set up the LLM (The "Brain")
llm = ChatGoogleGenerativeAI(model="models/gemini-pro-latest", temperature=0)

# 2. Define the Prompt with Memory
# We add a "MessagesPlaceholder" which is where the memory will be injected.
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
    MessagesPlaceholder(variable_name="chat_history"), # This is where memory goes
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# --- Part 1: Manage Conversation State (Short-Term Memory) ---
# We check if this user has a previous session saved.
if current_user_id in user_sessions:
    print("--- Welcome back! Loading your previous conversation. ---")
    memory = user_sessions[current_user_id]
else:
    print("--- Starting a new conversation. ---")
    # This memory object will store the conversation history.
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
# --- End of Part 1 ---

# 3. Create the Agent
agent = create_tool_calling_agent(llm, all_tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=all_tools, 
    verbose=True,
    memory=memory # We connect the memory to the agent
)

# 4. Test the Agent
print(f"Hello! I'm Ria. Your user ID is {current_user_id}. How can I help you today?")
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        # When the user exits, we save their conversation history.
        user_sessions[current_user_id] = memory
        print("Goodbye! Your conversation has been saved.")
        break
    
    try:
        result = agent_executor.invoke({
            "input": user_input
        })
        # The output is now automatically part of the conversation history.
        print(f"Ria: {result['output']}")
        
    except Exception as e:
        print("\nRia: I'm sorry, I've encountered a technical issue. Please try your request again shortly.")
        print(f"DEBUG_ERROR: {e}\n")
