from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.wallet import WalletBalanceOut, WalletHistoryOut

router = APIRouter()


@router.get("/balance", response_model=WalletBalanceOut, summary="Balance actual del usuario")
async def get_balance(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = client.table("user_balance").select("*").eq("user_id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Balance no encontrado")
    return WalletBalanceOut(**result.data)


@router.get("/history", response_model=List[WalletHistoryOut], summary="Historial completo de movimientos")
async def get_history(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("wallet_entries")
        .select("*")
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .range(skip, skip + limit - 1)
        .execute()
    )
    return [WalletHistoryOut(**r) for r in (result.data or [])]


@router.get("/history/recent", response_model=List[WalletHistoryOut], summary="Últimos 5 movimientos")
async def get_recent_history(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("wallet_entries")
        .select("*")
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    return [WalletHistoryOut(**r) for r in (result.data or [])]


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar entrada del wallet (soft delete)")
async def soft_delete_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    from datetime import datetime, timezone
    user_id = str(current_user.id)

    # Filtrar por user_id para evitar IDOR (un usuario no puede borrar entradas ajenas)
    result = (
        client.table("wallet_entries")
        .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", entry_id)
        .eq("user_id", user_id)  # FILTRO DE OWNERSHIP
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrada no encontrada")
