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

    # IziPay / micuentaweb.pe — Credenciales del comercio
    # Panel: https://panel.micuentaweb.pe → Desarrolladores → Claves
    IZIPAY_HMAC_KEY: str = ""        # Clave HMAC-SHA256 (verifica firma del webhook)
    IZIPAY_SHOP_USERNAME: str = ""   # Usuario / Identificador de tienda (ej: 61792228)
    IZIPAY_SHOP_PASSWORD: str = ""   # Contraseña de producción

    # Admin — Clave secreta para operaciones administrativas internas (ej: activación manual de Plus)
    # Generar con: python -c "import secrets; print(secrets.token_hex(32))"
    # En Railway (producción): configurar como variable de entorno ADMIN_SECRET_KEY
    # En .env local: ADMIN_SECRET_KEY=cualquier-valor-para-desarrollo
    ADMIN_SECRET_KEY: str = ""       # Vacío deshabilita el endpoint de activación manual

    # Google Gemini — API key para generación de descripciones de productos con IA
    # Panel: https://aistudio.google.com/app/apikey
    # En Railway: configurar como variable de entorno GEMINI_API_KEY
    GEMINI_API_KEY: str = ""         # Vacío deshabilita la generación con IA (usa fallback)

    # CORS – separar múltiples orígenes con coma en .env, ej: http://localhost:3000,https://mifrontend.com
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Cookie de refresco (refresh_token) — HttpOnly, Secure en producción
    # En .env local: COOKIE_SECURE=false
    # En Railway (producción): COOKIE_SECURE=true
    COOKIE_SECURE: bool = True
    COOKIE_DOMAIN: str = ""          # Dejar vacío para que aplique al dominio actual
    COOKIE_SAMESITE: str = "none"    # "none" es requerido si el frontend y backend están en dominios distintos
    COOKIE_MAX_AGE: int = 60 * 60 * 24 * 60  # 60 días (igual que refresh_token de Supabase)

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()

