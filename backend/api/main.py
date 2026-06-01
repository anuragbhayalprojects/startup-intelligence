import os
import sys

# Add 'backend' and 'repo root' directories to PYTHONPATH dynamically to prevent import errors during local run or deployment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client, Client
from api.routes import startups

load_dotenv()

app = FastAPI()

app.include_router(startups.router, prefix="/api")

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

@app.get("/")
def read_root():
    return {"Startup Intelligence: Backend Server is Running"}
