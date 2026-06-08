from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.marketplace import RewardOut, MarketItemOut, UserCouponOut, RedeemRewardRequest

router = APIRouter()


@router.get("/rewards", response_model=List[RewardOut], summary="Recompensas disponibles")
async def get_rewards(
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("rewards").select("*").eq("active", True).execute()
    return [RewardOut(**r) for r in (result.data or [])]


@router.get("/items", response_model=List[MarketItemOut], summary="Items del marketplace")
async def get_market_items(
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("market_items").select("*").eq("active", True).execute()
    return [MarketItemOut(**r) for r in (result.data or [])]


@router.get("/items/{item_id}", response_model=MarketItemOut, summary="Detalle de un item")
async def get_market_item(
    item_id: str,
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.table("market_items").select("*").eq("id", item_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return MarketItemOut(**result.data)


@router.get("/coupons", response_model=List[UserCouponOut], summary="Cupones del usuario")
async def get_user_coupons(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    result = (
        client.table("user_coupons")
        .select("*, rewards(*)")
        .eq("user_id", user_id)
        .execute()
    )
    return [UserCouponOut(**r) for r in (result.data or [])]


@router.post("/coupons", response_model=UserCouponOut, status_code=status.HTTP_201_CREATED, summary="Canjear recompensa")
async def redeem_reward(
    body: RedeemRewardRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    data = {"user_id": user_id, "reward_id": body.reward_id, "code": body.code}
    result = client.table("user_coupons").insert(data).select("*, rewards(*)").single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo canjear la recompensa")

    # Obtener info de la recompensa para la wallet
    reward = result.data.get("rewards")
    if reward:
        points = reward.get("points", 0)
        if points > 0:
            wallet_entry = {
                "user_id": user_id,
                "points": points,
                "type": "OUT",
                "title": f"Canje: {reward.get('title', 'Recompensa')}",
                "detail": "Marketplace",
                "emoji": "🎁",
                "related_coupon_id": result.data.get("id"),
            }
            client.table("wallet_entries").insert(wallet_entry).execute()

    return UserCouponOut(**result.data)
