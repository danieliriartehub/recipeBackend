from fastapi import APIRouter, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.schemas.simulator import MaterialOut

router = APIRouter()


# ── Catálogo de materiales ────────────────────────────────────────────────────

@router.get(
    "/materials",
    response_model=List[MaterialOut],
    summary="Catálogo de materiales reciclables",
    description=(
        "Devuelve la metadata estática de todos los materiales activos. "
        "Solo lectura — no realiza cálculos ni afecta saldos de usuario."
    ),
)
async def get_materials(
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("materials")
        .select("type, label, emoji, points_per_kg, co2_per_kg, trees_equivalent_per_kg")
        .eq("is_active", True)
        .order("type")
        .execute()
    )
    return [MaterialOut(**r) for r in (result.data or [])]
