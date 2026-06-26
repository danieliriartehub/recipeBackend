from fastapi import APIRouter, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client

router = APIRouter()


@router.get("/universities", summary="Ranking por universidades")
async def get_university_rankings(
    skip: int = 0,
    limit: int = 50,
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("university_rankings").select("*").range(skip, skip + limit - 1).execute()
    return result.data or []


@router.get("/weekly", summary="Top 10 líderes semanales")
async def get_weekly_leaders(
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("weekly_leaders").select("*").limit(10).execute()
    return result.data or []
