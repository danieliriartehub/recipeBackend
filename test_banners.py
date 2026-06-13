import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

client = create_client(url, key)
res = client.table("merchant_partners").select("id, business_name, banner_url").eq("is_active", True).execute()
for item in res.data:
    print(item)
