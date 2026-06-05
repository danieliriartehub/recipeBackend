from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    redirect_to: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    email_confirmed: bool = False


class SessionOut(BaseModel):
    """
    Solo expone el access_token en el body JSON.
    El refresh_token se transmite exclusivamente via cookie HttpOnly — nunca en el payload.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class LoginResponse(BaseModel):
    session: SessionOut


class RegisterResponse(BaseModel):
    needs_confirmation: bool
    session: Optional[SessionOut] = None


class RefreshResponse(BaseModel):
    """Respuesta del endpoint /refresh — solo el nuevo access_token."""
    access_token: str
    expires_in: int


class ProfileOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_initials: Optional[str] = None
    university_id: Optional[str] = None
    career: Optional[str] = None
    points: int = 0
    total_kg: float = 0
    co2_saved_kg: float = 0
    streak_days: int = 0
    level_index: int = 0
    weekly_goal_kg: float = 5
    qr_code: Optional[str] = None


class MeResponse(BaseModel):
    user: UserOut
    profile: Optional[ProfileOut] = None
