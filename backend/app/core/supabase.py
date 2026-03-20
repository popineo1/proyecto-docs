from supabase import create_client, Client
from app.core.config import settings

def get_supabase() -> Client | None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return None
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
