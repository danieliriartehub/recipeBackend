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

    from datetime import datetime, timezone
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        result = (
            client.table("profiles")
            .update(updates)
            .eq("id", user_id)
            .execute()
        )
    except Exception as e:
        # Supabase raises APIError on postgres errors (e.g. duplicate username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if not result.data or len(result.data) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return ProfileOut(**result.data[0])


@router.post("/me/qr-token", summary="Generar token QR del usuario")
async def generate_qr_token(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    import jwt
    import uuid
    from datetime import datetime, timezone, timedelta
    from app.core.config import settings

    user_id = str(current_user.id)
    
    # 1. Obtener perfil
    prof = client.table("profiles").select("full_name, qr_code, points").eq("id", user_id).single().execute()
    if not prof.data:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
        
    qr_code = prof.data.get("qr_code")
    if not qr_code:
        # Generar qr_code único si no tiene (p.ej. usuarios antiguos)
        qr_code = str(uuid.uuid4()).split("-")[0].upper()
        client.table("profiles").update({"qr_code": qr_code}).eq("id", user_id).execute()

    # 2. Generar JWT (1 minuto para máxima seguridad y coincidir con la UI)
    issued_at = datetime.now(timezone.utc)
    expires_in_minutes = 1
    expires_at = issued_at + timedelta(minutes=expires_in_minutes)
    
    payload = {
        "user_id": user_id,
        "full_name": prof.data.get("full_name") or "",
        "qr_code": qr_code,
        "points": prof.data.get("points") or 0,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "expires_at": expires_at.isoformat(),
        "issued_at": issued_at.isoformat(),
    }
    
    secret = settings.ADMIN_SECRET_KEY or settings.SUPABASE_SERVICE_KEY
    token = jwt.encode(payload, secret, algorithm="HS256")
    
    return {
        "token": token,
        "payload": payload,
        "expires_at": expires_at.isoformat(),
        "expires_in": expires_in_minutes * 60
    }
