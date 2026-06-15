from dotenv import load_dotenv
from pathlib import Path
import os

# Root project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from root
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Load externalized LLM configuration
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config", "llm_config.json")
_LLM_CFG = {}
if os.path.exists(_CONFIG_PATH):
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _LLM_CFG = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load llm_config.json: {e}")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or _LLM_CFG.get("ollama_base_url") or "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or _LLM_CFG.get("ollama_model") or "qwen2.5:3b"
OLLAMA_TIMEOUT = float(_LLM_CFG.get("request_timeout_seconds", 180.0))

print("SUPABASE_URL:", SUPABASE_URL)
print("OLLAMA_MODEL:", OLLAMA_MODEL)