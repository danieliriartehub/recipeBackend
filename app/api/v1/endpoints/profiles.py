from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.profiles import ProfileOut, ProfileUpdate

router = APIRouter()


@router.get("/me", response_model=ProfileOut, summary="Obtener perfil del usuario autenticado")
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = client.table("profiles").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return ProfileOut(**result.data)


@router.patch("/me", response_model=ProfileOut, summary="Actualizar perfil del usuario autenticado")
async def update_my_profile(
    body: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar")



    result = (
        client.table("profiles")
        .update(updates)
        .eq("id", user_id)
        .select()
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return ProfileOut(**result.data)


@router.post("/me/qr-token", summary="Generar token QR del usuario")
async def generate_qr_token(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = client.rpc("generate_qr_token", {"p_user_id": user_id}).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo generar el token QR")
    return result.data
