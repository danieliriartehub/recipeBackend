from supabase import create_client, Client
from app.core.config import settings

# Client con anon key – respeta Row Level Security
def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Client con service_role key – omite RLS (sólo para operaciones de servidor)
def get_supabase_admin_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
