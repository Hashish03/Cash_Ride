import os
from supabase import create_client
from django.conf import settings

# Production-ready Supabase client with error handling
class SupabaseClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = create_client(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_ANON_KEY")
            )
        return cls._instance

supabase = SupabaseClient().client