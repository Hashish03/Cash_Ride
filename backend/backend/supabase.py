from supabase import create_client, Client
from django.conf import settings

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

# Configure auth providers in Supabase dashboard for:
# Google, Facebook, Apple, GitHub, Twitter, etc.