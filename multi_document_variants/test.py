import os
from dotenv import load_dotenv

load_dotenv()
print("GEMINI_API_KEY =", repr(os.getenv("GEMINI_API_KEY")))
