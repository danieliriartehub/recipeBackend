from fastapi import APIRouter, Depends, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.scans import ScanCreate, ScanOut

router = APIRouter()


@router.get("/", response_model=List[ScanOut], summary="Historial de escaneos del usuario")
async def get_scan_history(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("scans")
        .select("*, centers(name)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
        .execute()
    )
    return [ScanOut(**r) for r in (result.data or [])]


@router.post("/", response_model=ScanOut, status_code=status.HTTP_201_CREATED, summary="Registrar un escaneo")
async def create_scan(
    body: ScanCreate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    data = body.model_dump()
    data["user_id"] = user_id
    result = client.table("scans").insert(data).select().single().execute()
    return ScanOut(**result.data)
