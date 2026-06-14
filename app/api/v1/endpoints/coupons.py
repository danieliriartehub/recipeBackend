from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.coupons import MerchantCouponHistoryOut

router = APIRouter()

@router.get("/history", response_model=List[MerchantCouponHistoryOut], summary="Historial de cupones usados")
async def get_coupons_history(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    
    try:
        # Realizar consulta join con supabase postgrest syntax
        result = (
            client.table("merchant_redemptions")
            .select(
                "id, points_spent, redemption_code, status, redeemed_at, expires_at, "
                "merchant_products (id, name, image_url, merchant_partners (business_name, logo_url))"
            )
            .eq("user_id", user_id)
            .eq("status", "redeemed")
            .order("redeemed_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consultando el historial de cupones: {str(e)}"
        )
        
    history = []
    for row in (result.data or []):
        product = row.get("merchant_products")
        if not product:
            continue
            
        partner = product.get("merchant_partners")
        if not partner:
            continue
            
        history_item = MerchantCouponHistoryOut(
            redemption_id=row.get("id"),
            product_id=product.get("id"),
            product_name=product.get("name"),
            partner_name=partner.get("business_name"),
            partner_logo=partner.get("logo_url"),
            image_url=product.get("image_url"),
            points_spent=row.get("points_spent"),
            redemption_code=row.get("redemption_code"),
            status=row.get("status"),
            redeemed_at=row.get("redeemed_at"),
            expires_at=row.get("expires_at")
        )
        history.append(history_item)
        
    return history


@router.get("/active", response_model=List[MerchantCouponHistoryOut], summary="Historial de cupones activos")
async def get_coupons_active(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    
    try:
        result = (
            client.table("merchant_redemptions")
            .select(
                "id, points_spent, redemption_code, status, redeemed_at, expires_at, "
                "merchant_products (id, name, image_url, merchant_partners (business_name, logo_url))"
            )
            .eq("user_id", user_id)
            .in_("status", ["pending", "validated"])
            .order("expires_at", desc=False)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consultando cupones activos: {str(e)}"
        )
        
    history = []
    for row in (result.data or []):
        product = row.get("merchant_products")
        if not product:
            continue
            
        partner = product.get("merchant_partners")
        if not partner:
            continue
            
        history_item = MerchantCouponHistoryOut(
            redemption_id=row.get("id"),
            product_id=product.get("id"),
            product_name=product.get("name"),
            partner_name=partner.get("business_name"),
            partner_logo=partner.get("logo_url"),
            image_url=product.get("image_url"),
            points_spent=row.get("points_spent"),
            redemption_code=row.get("redemption_code"),
            status=row.get("status"),
            redeemed_at=row.get("redeemed_at"),
            expires_at=row.get("expires_at")
        )
        history.append(history_item)
        
    return history


@router.get("/expired", response_model=List[MerchantCouponHistoryOut], summary="Historial de cupones expirados")
async def get_coupons_expired(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    
    try:
        result = (
            client.table("merchant_redemptions")
            .select(
                "id, points_spent, redemption_code, status, redeemed_at, expires_at, "
                "merchant_products (id, name, image_url, merchant_partners (business_name, logo_url))"
            )
            .eq("user_id", user_id)
            .eq("status", "expired")
            .order("expires_at", desc=True)
            .execute()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consultando cupones expirados: {str(e)}"
        )
        
    history = []
    for row in (result.data or []):
        product = row.get("merchant_products")
        if not product:
            continue
            
        partner = product.get("merchant_partners")
        if not partner:
            continue
            
        history_item = MerchantCouponHistoryOut(
            redemption_id=row.get("id"),
            product_id=product.get("id"),
            product_name=product.get("name"),
            partner_name=partner.get("business_name"),
            partner_logo=partner.get("logo_url"),
            image_url=product.get("image_url"),
            points_spent=row.get("points_spent"),
            redemption_code=row.get("redemption_code"),
            status=row.get("status"),
            redeemed_at=row.get("redeemed_at"),
            expires_at=row.get("expires_at")
        )
        history.append(history_item)
        
    return history
