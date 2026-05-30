import os
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
    return {"Hello": "World"}
