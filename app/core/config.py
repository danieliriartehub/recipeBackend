from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Recipe Backend API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str

    # CORS – separar múltiples orígenes con coma en .env, ej: http://localhost:3000,https://mifrontend.com
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Cookie de refresco (refresh_token) — HttpOnly, Secure en producción
    # En .env local: COOKIE_SECURE=false
    # En Railway (producción): COOKIE_SECURE=true
    COOKIE_SECURE: bool = True
    COOKIE_DOMAIN: str = ""          # Dejar vacío para que aplique al dominio actual
    COOKIE_SAMESITE: str = "strict"  # "strict" | "lax" | "none"
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 60  # 60 días (igual que refresh_token de Supabase)

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()

