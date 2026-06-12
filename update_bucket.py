import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

client = create_client(url, key)
res = client.storage.update_bucket("almacenamiento", options={"public": True})
print("Updated:", res)
