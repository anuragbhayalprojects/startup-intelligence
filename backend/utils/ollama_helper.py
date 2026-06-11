import os
import time
import requests
import subprocess
import platform
from backend.utils.config import OLLAMA_BASE_URL

# Cache to avoid pinging Ollama on every call in rapid succession
_last_check_time = 0.0
_last_status_checked = None  # None, True (online), or False (offline)

def ensure_ollama_running() -> bool:
    """
    Checks if the local Ollama service is running.
    If not, attempts to start it programmatically.
    Returns True if running/started successfully, False otherwise.
    """
    global _last_check_time, _last_status_checked
    
    current_time = time.time()
    # If checked within last 30 seconds, return the cached status
    if _last_status_checked is not None and (current_time - _last_check_time < 30.0):
        return _last_status_checked

    base_url = OLLAMA_BASE_URL or "http://localhost:11434"
    url = f"{base_url}/api/tags"
    
    # 1. Check if already running
    try:
        resp = requests.get(url, timeout=2.0)
        if resp.status_code == 200:
            _last_check_time = current_time
            _last_status_checked = True
            return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        pass

    print(f"⚠️ Ollama service is offline at {base_url}. Attempting to start it...")

    # 2. Try starting it programmatically
    started = False
    
    # On macOS (Darwin), try to open the Desktop application first
    if platform.system() == "Darwin":
        try:
            print("Trying to start Ollama application using 'open -a Ollama'...")
            subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            started = True
        except Exception as e:
            print(f"Failed to launch Ollama via open: {e}")

    # Fallback to 'ollama serve' CLI command if open didn't work or not on Mac
    if not started or platform.system() != "Darwin":
        try:
            print("Trying to start Ollama using 'ollama serve'...")
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            started = True
        except Exception as e:
            print(f"Failed to start Ollama using 'ollama serve': {e}")

    if not started:
        print("❌ Could not initiate any command to start Ollama.")
        _last_check_time = current_time
        _last_status_checked = False
        return False

    # 3. Poll tags endpoint to check when it becomes active
    max_retries = 20
    for i in range(max_retries):
        time.sleep(1.5)
        try:
            resp = requests.get(url, timeout=2.0)
            if resp.status_code == 200:
                print("✅ Ollama started successfully and is responding.")
                _last_check_time = time.time()
                _last_status_checked = True
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print(f"Waiting for Ollama to respond... ({i+1}/{max_retries})")

    print("❌ Ollama server startup timed out.")
    _last_check_time = time.time()
    _last_status_checked = False
    return False
