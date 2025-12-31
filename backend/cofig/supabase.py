import os
import logging
from supabase import create_client, Client
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        """Initialize Supabase client with error handling"""
        try:
            url = os.getenv("SUPABASE_URL") or settings.SUPABASE_URL
            key = os.getenv("SUPABASE_ANON_KEY") or settings.SUPABASE_ANON_KEY
            
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
            
            self._client = create_client(url, key)
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    @property
    def client(self) -> Client:
        """Get the Supabase client instance"""
        if self._client is None:
            self._initialize_client()
        return self._client

# Global instance
supabase = SupabaseClient().client