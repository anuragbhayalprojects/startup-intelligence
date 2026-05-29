from fastapi import APIRouter
from supabase import create_client
from dotenv import load_dotenv

import os

load_dotenv()

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# ---------------------------------------------------
# GET ALL STARTUPS
# ---------------------------------------------------

@router.get("/startups")
def get_startups():

    response = (
        supabase
        .table("startups")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data

# ---------------------------------------------------
# GET SINGLE STARTUP
# ---------------------------------------------------

@router.get("/startup/{startup_id}")
def get_startup(startup_id: str):

    response = (
        supabase
        .table("startups")
        .select("*")
        .eq("id", startup_id)
        .single()
        .execute()
    )

    return response.data

# ---------------------------------------------------
# SEARCH STARTUPS
# ---------------------------------------------------

@router.get("/search")
def search_startups(query: str):

    response = (
        supabase
        .table("startups")
        .select("*")
        .ilike("startup_name", f"%{query}%")
        .execute()
    )

    return response.data