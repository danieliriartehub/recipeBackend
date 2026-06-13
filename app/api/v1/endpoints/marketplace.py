from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.marketplace import RedeemProductRequest, RedemptionOut

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


import random
import string

@router.post("/redemptions", response_model=RedemptionOut, status_code=status.HTTP_201_CREATED, summary="Canjear un producto")
async def redeem_product(
    body: RedeemProductRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    product_id = body.product_id
    current_time_dt = datetime.now(timezone.utc)
    current_time = current_time_dt.isoformat()
    
    # 1. Validar Producto
    prod_result = (
        client.table("merchant_products")
        .select("*, merchant_partners!inner(*)")
        .eq("id", product_id)
        .eq("is_active", True)
        .eq("merchant_partners.is_active", True)
        .single()
        .execute()
    )
    if not prod_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado o inactivo")
        
    product = prod_result.data
    
    status_val = product.get("status")
    if status_val and status_val != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Producto no disponible")
        
    avail_from = product.get("available_from")
    if avail_from:
        from_dt = datetime.fromisoformat(avail_from.replace("Z", "+00:00"))
        if from_dt > current_time_dt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Producto aún no disponible")
            
    avail_until = product.get("available_until")
    if avail_until:
        until_dt = datetime.fromisoformat(avail_until.replace("Z", "+00:00"))
        if until_dt < current_time_dt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Producto expirado")
            
    stock = product.get("stock")
    if stock is not None and stock <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Producto sin stock")
        
    points_cost = product.get("points", 0)

    # 2. Validar Usuario y Puntos
    prof_result = client.table("profiles").select("points").eq("id", user_id).single().execute()
    if not prof_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
        
    user_points = prof_result.data.get("points", 0)
    if user_points < points_cost:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Puntos insuficientes")
        
    # 3. Descontar Puntos
    new_points = user_points - points_cost
    client.table("profiles").update({"points": new_points}).eq("id", user_id).execute()
    
    # 4. Descontar Stock (si aplica)
    if stock is not None:
        new_stock = stock - 1
        client.table("merchant_products").update({"stock": new_stock}).eq("id", product_id).execute()
        
    # 5. Generar Canje (Cupón)
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    redemption_data = {
        "user_id": user_id,
        "merchant_product_id": product_id,
        "points_spent": points_cost,
        "redemption_code": code,
        "status": "pending"
    }
    redemption_result = client.table("merchant_redemptions").insert(redemption_data).execute()
    
    if not redemption_result.data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al generar el canje")
        
    redemption = redemption_result.data[0]
    redemption_id = redemption.get("id")
    
    # 6. Historial Wallet
    wallet_entry = {
        "user_id": user_id,
        "points": points_cost,
        "type": "spent",
        "title": f"Canje: {product.get('name', 'Recompensa')}",
        "detail": "Marketplace",
        "emoji": "🎁",
    }
    client.table("wallet_entries").insert(wallet_entry).execute()
    
    # Formatear producto para la salida
    merchant_data = product.pop("merchant_partners")
    if "business_name" in merchant_data:
        merchant_data["name"] = merchant_data.pop("business_name")
    product["merchant"] = merchant_data
    if product.get("featured") is None:
        product["featured"] = False

    resp = redemption
    resp["product"] = product
    
    return RedemptionOut(**resp)
