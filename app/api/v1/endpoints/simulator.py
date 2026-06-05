from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List
import logging

from app.core.supabase import get_supabase_admin_client
from app.schemas.simulator import MaterialOut

router = APIRouter()
logger = logging.getLogger(__name__)


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
    try:
        result = (
            client.table("materials")
            .select("type, label, emoji, points_per_kg, co2_per_kg, trees_equivalent_per_kg")
            .eq("is_active", True)
            .order("type")
            .execute()
        )
    except Exception as exc:
        logger.exception("Error consultando tabla materials: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar materiales: {str(exc)}",
        )

    rows = result.data or []
    logger.debug("materials query returned %d rows", len(rows))

    try:
        return [MaterialOut(**r) for r in rows]
    except Exception as exc:
        logger.exception("Error deserializando materiales: %s | rows=%s", exc, rows)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar materiales: {str(exc)}",
        )
