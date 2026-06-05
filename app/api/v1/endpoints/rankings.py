from fastapi import APIRouter, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client

router = APIRouter()


@router.get("/universities", summary="Ranking por universidades")
async def get_university_rankings(
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("university_rankings").select("*").execute()
    return result.data or []


@router.get("/weekly", summary="Top 10 líderes semanales")
async def get_weekly_leaders(
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("weekly_leaders").select("*").limit(10).execute()
    return result.data or []
