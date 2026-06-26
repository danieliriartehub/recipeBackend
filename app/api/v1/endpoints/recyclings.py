from fastapi import APIRouter, Depends, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.recyclings import RecyclingCreate, RecyclingOut

router = APIRouter()


@router.get("/", response_model=List[RecyclingOut], summary="Historial de reciclajes del usuario")
async def get_recyclings(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("recyclings")
        .select("*, centers(name, district)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
        .execute()
    )
    return [RecyclingOut(**r) for r in (result.data or [])]


@router.post("/", response_model=RecyclingOut, status_code=status.HTTP_201_CREATED, summary="Registrar un reciclaje")
async def create_recycling(
    body: RecyclingCreate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    data = body.model_dump()
    data["user_id"] = user_id
    result = client.table("recyclings").insert(data).select().single().execute()
    
    # Registrar la entrada en la wallet
    points = data.get("points_earned", 0)
    if points > 0:
        wallet_entry = {
            "user_id": user_id,
            "points": points,
            "type": "earned",
            "title": f"Reciclaje de {data.get('material', 'material')}",
            "detail": "Reciclaje",
            "emoji": "♻️",
            "related_recycling_id": result.data.get("id"),
        }
        client.table("wallet_entries").insert(wallet_entry).execute()

    return RecyclingOut(**result.data)
