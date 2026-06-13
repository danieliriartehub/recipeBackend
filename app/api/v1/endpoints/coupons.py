from fastapi import APIRouter, Depends
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.coupons import CouponHistoryOut

router = APIRouter()


@router.get("/history", response_model=List[CouponHistoryOut], summary="Historial de cupones usados")
async def get_used_coupons_history(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id) if hasattr(current_user, "id") else str(current_user.get("id"))
    result = (
        client.table("user_coupons")
        .select("*, rewards(*)")
        .eq("user_id", user_id)
        .or_("status.eq.used,used_at.neq.null")
        .execute()
    )
    
    coupons = result.data or []
    history = []
    
    for c in coupons:
        reward = c.get("rewards") or {}
        history.append(CouponHistoryOut(
            coupon_id=c.get("id"),
            reward_id=c.get("reward_id"),
            title=reward.get("title"),
            brand=reward.get("brand"),
            emoji=reward.get("emoji"),
            code=c.get("code"),
            points_spent=reward.get("cost_points") if reward.get("cost_points") is not None else reward.get("points"),
            used_at=c.get("used_at")
        ))
        
    return history
