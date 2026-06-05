from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from typing import List, Optional

from app.core.supabase import get_supabase_admin_client
from app.schemas.centers import CenterOut

router = APIRouter()

CLOSED_STATUSES = ["cerrado", "mantenimiento"]
UNAVAILABLE_STATUSES = ["cerrado", "mantenimiento", "lleno"]


@router.get("/", response_model=List[CenterOut], summary="Todos los centros de reciclaje")
async def get_centers(
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("centers").select("*").order("status").execute()
    return [CenterOut(**r) for r in (result.data or [])]


@router.get("/available", response_model=List[CenterOut], summary="Centros disponibles (excluye cerrado/mantenimiento/lleno)")
async def get_available_centers(
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("centers")
        .select("id, name, district, address, lat, lng, status, accepted_materials, hours, wait_minutes, capacity, rating")
        .not_.in_("status", UNAVAILABLE_STATUSES)
        .execute()
    )
    return [CenterOut(**r) for r in (result.data or [])]


@router.get("/search", response_model=List[CenterOut], summary="Buscar centros por campus y/o material")
async def search_centers(
    campus: Optional[str] = Query(None),
    material: Optional[str] = Query(None),
    only_active: bool = Query(False),
    client: Client = Depends(get_supabase_admin_client),
):
    query = client.table("centers").select("*")
    if campus:
        query = query.ilike("address", f"%{campus}%")
    if material:
        query = query.contains("accepted_materials", [material])
    if only_active:
        query = query.not_.in_("status", CLOSED_STATUSES)
    result = query.execute()
    return [CenterOut(**r) for r in (result.data or [])]


@router.get("/by-material", response_model=List[CenterOut], summary="Centros que aceptan un material específico")
async def get_centers_by_material(
    material: str = Query(...),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("centers")
        .select("*")
        .contains("accepted_materials", [material])
        .not_.in_("status", CLOSED_STATUSES)
        .execute()
    )
    return [CenterOut(**r) for r in (result.data or [])]


@router.get("/{center_id}", response_model=CenterOut, summary="Detalle de un centro")
async def get_center(
    center_id: str,
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("centers").select("*").eq("id", center_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centro no encontrado")
    return CenterOut(**result.data)
