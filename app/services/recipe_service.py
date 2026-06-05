"""
services/recipe_service.py
--------------------------
Toda la lógica de negocio relacionada con recetas.
Los endpoints sólo llaman a estos métodos – nunca tocan Supabase directamente.
"""
from typing import List, Optional
from supabase import Client

from app.schemas.recipe import RecipeCreate, RecipeUpdate


TABLE = "recipes"


class RecipeService:
    def __init__(self, client: Client):
        self.client = client

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all(self, limit: int = 50, offset: int = 0) -> List[dict]:
        response = (
            self.client.table(TABLE)
            .select("*")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data

    def get_by_id(self, recipe_id: str) -> Optional[dict]:
        response = (
            self.client.table(TABLE)
            .select("*")
            .eq("id", recipe_id)
            .single()
            .execute()
        )
        return response.data

    def get_by_user(self, user_id: str) -> List[dict]:
        response = (
            self.client.table(TABLE)
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return response.data

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, payload: RecipeCreate, user_id: str) -> dict:
        data = payload.model_dump()
        data["user_id"] = user_id
        response = self.client.table(TABLE).insert(data).execute()
        return response.data[0]

    def update(self, recipe_id: str, payload: RecipeUpdate) -> dict:
        data = payload.model_dump(exclude_none=True)
        response = (
            self.client.table(TABLE)
            .update(data)
            .eq("id", recipe_id)
            .execute()
        )
        return response.data[0]

    def delete(self, recipe_id: str) -> bool:
        self.client.table(TABLE).delete().eq("id", recipe_id).execute()
        return True
