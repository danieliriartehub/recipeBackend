import os, sys, traceback
from datetime import datetime, timezone
from supabase import create_client
import json

try:
    c = create_client('https://npcwicrgwvplwwzlryvx.supabase.co', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5wY3dpY3Jnd3ZwbHd3emxyeXZ4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTc0NjU4MCwiZXhwIjoyMDk1MzIyNTgwfQ.Ifk1uPcrfXFQIa3e9UwCo_n0S3eaPlKtReXJ6Dx9HvA')
    result = c.table('merchant_products').select('*, merchant_partners!inner(*)').eq('is_active', True).eq('merchant_partners.is_active', True).execute()
    data = []
    current_time_dt = datetime.now(timezone.utc)
    for r in (result.data or []):
        status_val = r.get('status')
        if status_val and status_val != 'active':
            continue
        avail_from = r.get('available_from')
        if avail_from:
            from_dt = datetime.fromisoformat(avail_from.replace('Z', '+00:00'))
        avail_until = r.get('available_until')
        if avail_until:
            until_dt = datetime.fromisoformat(avail_until.replace('Z', '+00:00'))
        if 'merchant_partners' in r:
            r['merchant'] = r.pop('merchant_partners')
        # Simulate Pydantic
        print(json.dumps(r, indent=2))
        from app.schemas.aliados import MarketplaceProductOut
        MarketplaceProductOut(**r)
    print("SUCCESS")
except Exception as e:
    traceback.print_exc()
