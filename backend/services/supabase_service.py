from supabase import create_client
from backend.utils.config import SUPABASE_URL, SUPABASE_KEY

print("SUPABASE_URL:", SUPABASE_URL)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def check_existing_startup(startup_name):

    response = (
        supabase
        .table("startups")
        .select("*")
        .eq("startup_name", startup_name)
        .execute()
    )

    if response.data and len(response.data) > 0:
        return response.data[0]

    return None


def insert_startup(data):

    response = (
        supabase
        .table("startups")
        .insert(data)
        .execute()
    )

    print(f"Inserted startup: {data.get('startup_name')}")

    return response.data


def update_startup(startup_id, data):

    response = (
        supabase
        .table("startups")
        .update(data)
        .eq("id", startup_id)
        .execute()
    )

    print(f"Updated startup: {data.get('startup_name')}")

    return response.data


def upsert_startup(data):

    existing = check_existing_startup(
        data.get("startup_name")
    )

    if existing:

        print(
            f"Startup already exists. Updating: "
            f"{data.get('startup_name')}"
        )

        return update_startup(
            existing["id"],
            data
        )

    print(
        f"New startup detected. Inserting: "
        f"{data.get('startup_name')}"
    )

    return insert_startup(data)