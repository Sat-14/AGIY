import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    # Configure the API key
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    print("Successfully configured API key. Fetching available models...")
    print("-" * 20)

    # List all available models
    for m in genai.list_models():
        # Check if the model supports the 'generateContent' method needed by LangChain
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model found: {m.name}")

    print("-" * 20)
    print("\nPlease copy one of the model names from the list above and use it in main.py")

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure your GOOGLE_API_KEY in the .env file is correct and the Generative Language API is enabled in your Google Cloud project.")
