from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.marketplace import RewardOut, MarketItemOut, UserCouponOut, RedeemRewardRequest

router = APIRouter()


from typing import Optional
from datetime import datetime, timezone
from app.schemas.aliados import MarketplaceProductOut, MarketplaceProductListOut, MarketplaceMerchantOut, MerchantPartnerOut

@router.get("/merchants", response_model=List[MarketplaceMerchantOut], summary="Obtener lista de aliados activos")
async def get_marketplace_merchants(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_partners")
        .select("id, business_name, logo_url")
        .eq("is_active", True)
        .execute()
    )
    
    data = []
    for r in (result.data or []):
        if "business_name" in r:
            r["name"] = r.pop("business_name")
        data.append(MarketplaceMerchantOut(**r))
        
    return data


@router.get("/merchants/{merchant_id}", response_model=MerchantPartnerOut, summary="Detalle de un aliado")
async def get_marketplace_merchant(
    merchant_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_partners")
        .select("*")
        .eq("id", merchant_id)
        .eq("is_active", True)
        .single()
        .execute()
    )
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliado no encontrado")
        
    r = result.data
    if "business_name" in r:
        r["name"] = r.pop("business_name")
        
    return MerchantPartnerOut(**r)


@router.get("/categories", response_model=List[str], summary="Obtener categorías de productos")
async def get_marketplace_categories(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_products")
        .select("category")
        .eq("is_active", True)
        .execute()
    )
    categories = set()
    for r in (result.data or []):
        cat = r.get("category")
        if cat:
            categories.add(cat)
    return sorted(list(categories))


@router.get("/products", response_model=List[MarketplaceProductListOut], summary="Catálogo consolidado del marketplace")
async def get_marketplace_products(
    search_query: Optional[str] = None,
    merchant_partner_id: Optional[str] = None,
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    current_time = datetime.now(timezone.utc).isoformat()
    
    query = (
        client.table("merchant_products")
        .select("*, merchant_partners!inner(*)")
        .eq("is_active", True)
        .eq("merchant_partners.is_active", True)
    )
    
    if search_query:
        query = query.ilike("name", f"%{search_query}%")
    if merchant_partner_id:
        query = query.eq("merchant_partner_id", merchant_partner_id)
    if category:
        query = query.eq("category", category)
    if featured is not None:
        query = query.eq("featured", featured)
        
    result = query.execute()
    
    data = []
    current_time_dt = datetime.now(timezone.utc)
    for r in (result.data or []):
        status_val = r.get("status")
        if status_val and status_val != "active":
            continue
            
        avail_from = r.get("available_from")
        if avail_from:
            from_dt = datetime.fromisoformat(avail_from.replace("Z", "+00:00"))
            if from_dt > current_time_dt:
                continue
                
        avail_until = r.get("available_until")
        if avail_until:
            until_dt = datetime.fromisoformat(avail_until.replace("Z", "+00:00"))
            if until_dt < current_time_dt:
                continue

        if "merchant_partners" in r:
            merchant_data = r.pop("merchant_partners")
            if "business_name" in merchant_data:
                merchant_data["name"] = merchant_data.pop("business_name")
            r["merchant"] = merchant_data
            
        if r.get("featured") is None:
            r["featured"] = False

        data.append(MarketplaceProductListOut(**r))
        
    return data


@router.get("/products/{product_id}", response_model=MarketplaceProductOut, summary="Detalle de un producto")
async def get_marketplace_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_products")
        .select("*, merchant_partners!inner(*)")
        .eq("id", product_id)
        .eq("is_active", True)
        .eq("merchant_partners.is_active", True)
        .single()
        .execute()
    )
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
        
    r = result.data
    current_time_dt = datetime.now(timezone.utc)
    
    status_val = r.get("status")
    if status_val and status_val != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no disponible")
        
    avail_from = r.get("available_from")
    if avail_from:
        from_dt = datetime.fromisoformat(avail_from.replace("Z", "+00:00"))
        if from_dt > current_time_dt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto aún no disponible")
            
    avail_until = r.get("available_until")
    if avail_until:
        until_dt = datetime.fromisoformat(avail_until.replace("Z", "+00:00"))
        if until_dt < current_time_dt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto expirado")

    merchant_data = r.pop("merchant_partners")
    if "business_name" in merchant_data:
        merchant_data["name"] = merchant_data.pop("business_name")
    r["merchant"] = merchant_data
    
    if r.get("featured") is None:
        r["featured"] = False

    return MarketplaceProductOut(**r)


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
