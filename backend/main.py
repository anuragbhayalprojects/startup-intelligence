import os
import sys

# Add the parent directory of backend (the project root) to sys.path to enable 'backend' absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Redirect to the main app instance in backend/api/main.py
from backend.api.main import app, supabase
