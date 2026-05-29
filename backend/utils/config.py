from dotenv import load_dotenv
from pathlib import Path
import os

# Root project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from root
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

print("SUPABASE_URL:", SUPABASE_URL)
print("OLLAMA_MODEL:", OLLAMA_MODEL)