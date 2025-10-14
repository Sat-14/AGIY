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
    ("system", """You are Ria, a friendly and knowledgeable fashion expert for ABFRL.
    Your goal is to help users find the perfect outfit and assist them with their needs.
    You are an expert on fashion, trends, materials, and our brand's entire catalog.
    Be proactive, encouraging, and positive. Always be helpful.
    You have access to a set of tools to help customers.
    Based on the user's request, select the best tool to use."""),
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
