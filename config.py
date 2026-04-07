from python_dotenv import load_dotenv

load_dotenv()

PORT=int(os.getenv("PORT", 80))
HOST=os.getenv("HOST", "127.0.0.1")