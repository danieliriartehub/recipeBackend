import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from supabase import Client

from app.core.config import settings
from app.core.supabase import get_supabase_client, get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ForgotPasswordRequest,
    RefreshResponse,
    MeResponse,
    ProfileOut,
    SessionOut,
    UserOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Nombre de la cookie que lleva el refresh_token ───────────────────────────
REFRESH_COOKIE = "recipe-refresh"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_user_out(user) -> UserOut:
    meta = user.user_metadata or {}
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=meta.get("full_name"),
        email_confirmed=user.email_confirmed_at is not None,
    )


def _build_session_out(session) -> SessionOut:
    """Solo expone el access_token en el body. El refresh_token va en cookie."""
    return SessionOut(
        access_token=session.access_token,
        expires_in=session.expires_in,
        user=_build_user_out(session.user),
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Escribe el refresh_token en una cookie HttpOnly para sacarlo del alcance de JS."""
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,      # type: ignore[arg-type]
        max_age=settings.COOKIE_MAX_AGE,
        domain=settings.COOKIE_DOMAIN or None,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,      # type: ignore[arg-type]
        path="/",
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión")
async def login(
    body: LoginRequest,
    response: Response,
    client: Client = Depends(get_supabase_client),
):
    """
    Autentica al usuario con email y contraseña.
    - Devuelve el `access_token` en el body JSON (para uso en memoria en el cliente).
    - Guarda el `refresh_token` en una cookie HttpOnly (invisible para JavaScript).
    """
    try:
        result = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        ) from e

    if result.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    _set_refresh_cookie(response, result.session.refresh_token)
    return LoginResponse(session=_build_session_out(result.session))


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, summary="Registrar usuario")
async def register(
    body: RegisterRequest,
    response: Response,
    client: Client = Depends(get_supabase_client),
):
    """
    Registra un nuevo usuario.
    Si Supabase no requiere confirmación de correo, también emite la cookie de refresco.
    """
    try:
        result = client.auth.sign_up(
            {
                "email": body.email,
                "password": body.password,
                "options": {"data": {"full_name": body.full_name}},
            }
        )
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este correo ya tiene una cuenta.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        ) from e

    if result.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el usuario.",
        )

    needs_confirmation = result.session is None
    session_out = None
    if result.session:
        _set_refresh_cookie(response, result.session.refresh_token)
        session_out = _build_session_out(result.session)

    return RegisterResponse(
        needs_confirmation=needs_confirmation,
        session=session_out,
    )


@router.post("/refresh", response_model=RefreshResponse, summary="Renovar access_token")
async def refresh_token(
    request: Request,
    response: Response,
    client: Client = Depends(get_supabase_client),
):
    """
    Lee el refresh_token desde la cookie HttpOnly y emite un nuevo access_token.
    Este endpoint es llamado automáticamente por el frontend al arrancar o cuando
    el access_token en memoria está a punto de expirar.
    """
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sin sesión activa. Inicia sesión nuevamente.",
        )

    try:
        result = client.auth.refresh_session(token)
    except Exception as e:
        # El refresh_token expiró o fue revocado — limpiar cookie y forzar re-login
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada. Inicia sesión nuevamente.",
        ) from e

    if result.session is None:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo renovar la sesión.",
        )

    # Rotar el refresh_token (Supabase emite uno nuevo en cada refresh)
    _set_refresh_cookie(response, result.session.refresh_token)
    return RefreshResponse(
        access_token=result.session.access_token,
        expires_in=result.session.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    """
    Invalida el token en Supabase y borra la cookie de refresco.
    Requiere el header: Authorization: Bearer <access_token>
    """
    try:
        client.auth.sign_out()
    except Exception as e:
        logger.warning(f"[AUTH] sign_out en servidor falló (se ignora): {e}")
    finally:
        _clear_refresh_cookie(response)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT, summary="Recuperar contraseña")
async def forgot_password(
    body: ForgotPasswordRequest,
    client: Client = Depends(get_supabase_client),
):
    """
    Envía un correo de recuperación de contraseña.
    """
    options = {}
    if body.redirect_to:
        options["redirect_to"] = body.redirect_to

    try:
        client.auth.reset_password_for_email(body.email, options)
    except Exception as e:
        logger.error(f"[AUTH] Error al recuperar contraseña para {body.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error procesando la recuperación de contraseña.",
        ) from e


@router.get("/me", response_model=MeResponse, summary="Usuario autenticado + perfil")
async def me(
    current_user: dict = Depends(get_current_user),
    admin_client: Client = Depends(get_supabase_admin_client),
):
    """
    Retorna los datos del usuario autenticado y su perfil de la tabla `profiles`.
    Requiere el header: Authorization: Bearer <access_token>
    """
    user_id = str(current_user.id)
    user_out = _build_user_out(current_user)

    profile_out = None
    try:
        result = (
            admin_client.table("profiles")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if result.data:
            profile_out = ProfileOut(**result.data)
    except Exception:
        pass  # Perfil aún no creado (usuario nuevo); retornamos sin perfil

    return MeResponse(user=user_out, profile=profile_out)
