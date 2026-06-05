from fastapi import APIRouter, Depends, status
from supabase import Client
from typing import List
from datetime import date

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.missions import MissionOut, BadgeOut, ChallengeOut, CompleteMissionRequest

router = APIRouter()


@router.get("/", response_model=List[MissionOut], summary="Misiones activas con progreso del usuario")
async def get_missions(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    today = date.today().isoformat()
    result = (
        client.table("missions")
        .select(f"*, user_missions!left(done, completed_at, period_start).eq(user_id, {user_id}).eq(period_start, {today})")
        .eq("active", True)
        .execute()
    )
    return [MissionOut(**r) for r in (result.data or [])]


@router.post("/complete", status_code=status.HTTP_204_NO_CONTENT, summary="Completar una misión")
async def complete_mission(
    body: CompleteMissionRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    from datetime import datetime, timezone
    client.table("user_missions").upsert({
        "user_id": user_id,
        "mission_id": body.mission_id,
        "done": True,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "period_start": body.period_start.isoformat(),
    }).execute()


@router.get("/badges", response_model=List[BadgeOut], summary="Badges del usuario")
async def get_badges(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("badges")
        .select(f"*, user_badges!left(unlocked_at).eq(user_id, {user_id})")
        .execute()
    )
    return [BadgeOut(**r) for r in (result.data or [])]


@router.get("/challenges", response_model=List[ChallengeOut], summary="Desafíos activos con progreso del usuario")
async def get_challenges(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("challenges")
        .select(f"*, user_challenges!left(progress, completed).eq(user_id, {user_id})")
        .eq("active", True)
        .execute()
    )
    return [ChallengeOut(**r) for r in (result.data or [])]
