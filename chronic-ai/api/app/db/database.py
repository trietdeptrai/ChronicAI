from typing import Optional
from supabase import create_client, Client
from app.config import settings

# Lazy-loaded Supabase client
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """
    Get Supabase client instance (lazy-loaded).
    
    Raises:
        ValueError: If Supabase credentials are not configured
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise ValueError(
                "Supabase credentials not configured. "
                "Set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
            )
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )
    
    return _supabase_client
