"""
api/v1/endpoints/recipes.py
----------------------------
Router de recetas – sólo orquesta: valida input, llama al service, devuelve response.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.supabase import get_supabase_client
from app.core.dependencies import get_current_user
from app.schemas.recipe import RecipeCreate, RecipeUpdate, RecipeResponse
from app.services.recipe_service import RecipeService

router = APIRouter()


def get_recipe_service(client: Client = Depends(get_supabase_client)) -> RecipeService:
    return RecipeService(client)


@router.get("/", response_model=List[RecipeResponse], summary="Listar recetas")
async def list_recipes(
    limit: int = 50,
    offset: int = 0,
    service: RecipeService = Depends(get_recipe_service),
):
    return service.get_all(limit=limit, offset=offset)


@router.get("/{recipe_id}", response_model=RecipeResponse, summary="Obtener receta")
async def get_recipe(
    recipe_id: str,
    service: RecipeService = Depends(get_recipe_service),
):
    recipe = service.get_by_id(recipe_id)
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return recipe


@router.post("/", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED, summary="Crear receta")
async def create_recipe(
    payload: RecipeCreate,
    current_user: dict = Depends(get_current_user),
    service: RecipeService = Depends(get_recipe_service),
):
    return service.create(payload, user_id=current_user.id)


@router.patch("/{recipe_id}", response_model=RecipeResponse, summary="Actualizar receta")
async def update_recipe(
    recipe_id: str,
    payload: RecipeUpdate,
    current_user: dict = Depends(get_current_user),
    service: RecipeService = Depends(get_recipe_service),
):
    return service.update(recipe_id, payload)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar receta")
async def delete_recipe(
    recipe_id: str,
    current_user: dict = Depends(get_current_user),
    service: RecipeService = Depends(get_recipe_service),
):
    service.delete(recipe_id)
