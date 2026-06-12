import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

client = create_client(url, key)
buckets = client.storage.list_buckets()
for b in buckets:
    print(b.name, b.public)
