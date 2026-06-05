from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Recipe Backend API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str          # anon/public key (for RLS-aware calls)
    SUPABASE_SERVICE_KEY: str  # service_role key (bypasses RLS, use with care)

    # CORS – lista separada por comas en .env, ej: http://localhost:3000,https://mifrontend.com
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
