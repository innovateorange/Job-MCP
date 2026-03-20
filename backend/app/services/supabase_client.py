import os

from fastapi import HTTPException
from supabase import Client, create_client


def get_supabase_client() -> Client:
    """Build a Supabase client for server-side writes."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise HTTPException(
            status_code=500,
            detail="Supabase environment variables are missing. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY).",
        )

    return create_client(supabase_url, supabase_key)
