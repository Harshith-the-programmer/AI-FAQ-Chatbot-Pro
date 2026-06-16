from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    print("API Key Loaded Successfully")
else:
    print("API Key Not Found")