from dotenv import load_dotenv
from pathlib import Path
import os
import json

# Root project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from root
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Load externalized LLM configuration
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config", "model_routing.json")
_MODEL_CFG = {}
if os.path.exists(_CONFIG_PATH):
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _MODEL_CFG = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load model_routing.json: {e}")

_ollama_cfg = _MODEL_CFG.get("ollama", {})

# --- Ollama (Local AI — always available as fallback) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or _ollama_cfg.get("default_base_url") or "http://localhost:11434"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or _ollama_cfg.get("default_model") or "qwen2.5:3b"
OLLAMA_TIMEOUT = float(_ollama_cfg.get("timeout_seconds", 120.0))

# --- OpenRouter (Cloud AI — primary provider when enabled) ---
# OPENROUTER_ENABLED is the master switch. If key is absent, auto-falls back to Ollama.
OPENROUTER_ENABLED = os.getenv("OPENROUTER_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip() or None
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

# Effective active provider (for logging/observability)
_active_provider = "openrouter" if (OPENROUTER_ENABLED and OPENROUTER_API_KEY) else "ollama"

print("SUPABASE_URL:", SUPABASE_URL)
print("OLLAMA_MODEL:", OLLAMA_MODEL)
print(f"AI Provider: {_active_provider.upper()} (OPENROUTER_ENABLED={OPENROUTER_ENABLED}, key={'SET' if OPENROUTER_API_KEY else 'NOT SET'})")