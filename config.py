from python_dotenv import load_dotenv
import os

load_dotenv()

PORT=int(os.getenv("PORT", 80))
HOST=os.getenv("HOST", "127.0.0.1")