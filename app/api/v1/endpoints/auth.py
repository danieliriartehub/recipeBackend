from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.supabase import get_supabase_client, get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ForgotPasswordRequest,
    MeResponse,
    ProfileOut,
    SessionOut,
    UserOut,
)

router = APIRouter()


def _build_user_out(user) -> UserOut:
    meta = user.user_metadata or {}
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=meta.get("full_name"),
        email_confirmed=user.email_confirmed_at is not None,
    )


def _build_session_out(session) -> SessionOut:
    return SessionOut(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        user=_build_user_out(session.user),
    )


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión")
async def login(
    body: LoginRequest,
    client: Client = Depends(get_supabase_client),
):
    """
    Autentica al usuario con email y contraseña.
    Retorna el access_token JWT y refresh_token para usar en peticiones protegidas.
    """
    try:
        response = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        ) from e

    if response.session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    return LoginResponse(session=_build_session_out(response.session))


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, summary="Registrar usuario")
async def register(
    body: RegisterRequest,
    client: Client = Depends(get_supabase_client),
):
    """
    Registra un nuevo usuario. Si Supabase requiere confirmación de correo,
    `needs_confirmation` será True y `session` será null hasta que confirme.
    """
    try:
        response = client.auth.sign_up(
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

    if response.user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo crear el usuario.",
        )

    needs_confirmation = response.session is None
    session_out = _build_session_out(response.session) if response.session else None

    return RegisterResponse(
        needs_confirmation=needs_confirmation,
        session=session_out,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
async def logout(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_client),
):
    """
    Invalida el token de sesión actual en Supabase.
    Requiere el header: Authorization: Bearer <access_token>
    """
    try:
        client.auth.sign_out()
    except Exception:
        pass  # Si falla el sign_out en servidor, el cliente igual debe limpiar su sesión


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT, summary="Recuperar contraseña")
async def forgot_password(
    body: ForgotPasswordRequest,
    client: Client = Depends(get_supabase_client),
):
    """
    Envía un correo de recuperación de contraseña.
    El `redirect_to` debe apuntar a la URL del frontend que maneja el reset.
    """
    options = {}
    if body.redirect_to:
        options["redirect_to"] = body.redirect_to

    try:
        client.auth.reset_password_for_email(body.email, options)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
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

    # Fetch profile from profiles table
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
        # Perfil aún no creado (usuario nuevo); retornamos sin perfil
        pass

    return MeResponse(user=user_out, profile=profile_out)
