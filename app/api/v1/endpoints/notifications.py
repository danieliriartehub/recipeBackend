from fastapi import APIRouter, Depends, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.notifications import NotificationOut, UnreadCountOut

router = APIRouter()


@router.get("/", response_model=List[NotificationOut], summary="Notificaciones del usuario")
async def get_notifications(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = client.table("notifications").select("*").eq("user_id", user_id).execute()
    return [NotificationOut(**r) for r in (result.data or [])]


@router.get("/unread-count", response_model=UnreadCountOut, summary="Cantidad de notificaciones no leídas")
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("read", False)
        .execute()
    )
    return UnreadCountOut(count=result.count or 0)


@router.patch("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT, summary="Marcar notificación como leída")
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    client.table("notifications").update({"read": True}).eq("id", notification_id).execute()


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT, summary="Marcar todas las notificaciones como leídas")
async def mark_all_read(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    client.table("notifications").update({"read": True}).eq("user_id", user_id).execute()
