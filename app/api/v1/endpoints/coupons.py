from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List
from datetime import datetime, timezone

import logging

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.coupons import (
    MerchantCouponHistoryOut,
    CouponValidateOut,
    CouponRedeemRequest,
    CouponRedeemOut
)

logger = logging.getLogger(__name__)

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
        logger.error(f"[COUPONS] Error consultando el historial de cupones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando el historial de cupones"
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
        logger.error(f"[COUPONS] Error consultando cupones activos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando cupones activos"
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
        logger.error(f"[COUPONS] Error consultando cupones expirados: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando cupones expirados"
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


@router.get("/validate/{code}", response_model=CouponValidateOut, summary="Validar código de cupón para aliados")
async def validate_coupon(
    code: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    try:
        user_res = client.table("merchant_users").select("merchant_partner_id").eq("id", current_user.id).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=403, detail="No autorizado")
        partner_id = user_res.data["merchant_partner_id"]
    except Exception:
        raise HTTPException(status_code=403, detail="No autorizado")

    try:
        result = (
            client.table("merchant_redemptions")
            .select(
                "id, points_spent, redemption_code, status, expires_at, "
                "merchant_products(id, name, merchant_partner_id, merchant_partners(business_name))"
            )
            .ilike("redemption_code", code.strip())
            .single()
            .execute()
        )
    except Exception as e:
        if hasattr(e, "code") and e.code == "PGRST116":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró el código ingresado."
            )
        logger.error(f"[COUPONS] DB Error validando cupón: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno validando el código."
        )

    if not result.data:
        raise HTTPException(status_code=404, detail="No se encontró el código ingresado.")

    row = result.data
    product = row.get("merchant_products")
    
    if product.get("merchant_partner_id") != partner_id:
        raise HTTPException(status_code=403, detail="No autorizado para consultar este cupón.")

    partner = product.get("merchant_partners", {})
    
    return CouponValidateOut(
        redemption_id=row.get("id"),
        product_id=product.get("id"),
        product_name=product.get("name"),
        partner_name=partner.get("business_name", ""),
        points_spent=row.get("points_spent"),
        redemption_code=row.get("redemption_code"),
        status=row.get("status"),
        expires_at=row.get("expires_at")
    )


@router.post("/redeem", response_model=CouponRedeemOut, summary="Canjear cupón")
async def redeem_coupon(
    payload: CouponRedeemRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    try:
        user_res = client.table("merchant_users").select("merchant_partner_id").eq("id", current_user.id).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=403, detail="No autorizado")
        partner_id = user_res.data["merchant_partner_id"]
    except Exception:
        raise HTTPException(status_code=403, detail="No autorizado")

    try:
        result = (
            client.table("merchant_redemptions")
            .select("id, status, merchant_products(merchant_partner_id)")
            .eq("id", payload.redemption_id)
            .single()
            .execute()
        )
    except Exception as e:
        if hasattr(e, "code") and e.code == "PGRST116":
            raise HTTPException(status_code=404, detail="No se encontró el cupón.")
        logger.error(f"[COUPONS] DB Error obteniendo cupón a canjear: {e}")
        raise HTTPException(status_code=500, detail="Error de base de datos interno.")

    if not result.data:
        raise HTTPException(status_code=404, detail="No se encontró el cupón.")

    row = result.data
    
    if row.get("merchant_products", {}).get("merchant_partner_id") != partner_id:
        raise HTTPException(status_code=403, detail="No autorizado")

    coupon_status = row.get("status")
    if coupon_status == "redeemed":
        raise HTTPException(status_code=400, detail="Este cupón ya fue canjeado.")
    if coupon_status == "expired":
        raise HTTPException(status_code=400, detail="Este cupón ha expirado.")
    if coupon_status == "cancelled":
        raise HTTPException(status_code=400, detail="Este cupón ha sido cancelado.")
    if coupon_status != "pending":
        raise HTTPException(status_code=400, detail="El cupón no está disponible para canje.")

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        client.table("merchant_redemptions").update({
            "status": "redeemed",
            "redeemed_at": now_iso
        }).eq("id", payload.redemption_id).execute()
    except Exception as e:
        logger.error(f"[COUPONS] Error registrando canje en DB: {e}")
        raise HTTPException(status_code=500, detail="Error interno al registrar canje.")

    return CouponRedeemOut(success=True, message="Canje registrado correctamente.")
