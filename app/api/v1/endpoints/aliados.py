from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from supabase import Client
from typing import List, Optional, Any
from datetime import datetime, timezone
from postgrest.exceptions import APIError
from datetime import datetime, timezone

from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.aliados import (
    MerchantProductCreate,
    MerchantProductUpdate,
    MerchantProductOut,
    MerchantPartnerUpdate,
    MerchantPartnerOut,
    MerchantUserOut,
    ValidatorOut,
    ValidateQrRequest,
    ValidateQrOut,
    CreateDeliverySessionRequest,
    AddDeliveryItemRequest,
    RemoveDeliveryItemRequest,
    ConfirmDeliveryRequest,
    RegisterRecyclingRequest,
    MarketplaceProductOut,
    MerchantBannerCreate,
    MerchantBannerUpdate,
    MerchantBannerOut,
)

router = APIRouter()


# ── Whoami: detecta rol en una sola llamada ───────────────────────────────────

@router.get("/whoami", summary="Detecta el rol del usuario autenticado (operador o aliado)")
async def whoami(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    """
    Devuelve { role: 'operador' | 'aliado', ...perfil } en una sola petición.
    Evita que el frontend haga dos llamadas secuenciales de prueba-y-error.
    """
    user_id = str(current_user.id)

    # 1. ¿Es operador?
    try:
        result = (
            client.table("validators")
            .select("id, full_name, center_id, centers(name)")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if result.data:
            return {"role": "operador", **result.data}
    except APIError as e:
        if e.code != "PGRST116":
            raise

    # 2. ¿Es aliado (merchant)?
    try:
        result = (
            client.table("merchant_users")
            .select("*, merchant_partners(*)")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if result.data:
            return {"role": "aliado", **result.data}
    except APIError as e:
        if e.code != "PGRST116":
            raise

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no registrado como aliado u operador")


# ── Merchant: perfil ──────────────────────────────────────────────────────────

@router.get("/me", response_model=MerchantUserOut, summary="Perfil del aliado autenticado")
async def get_merchant_me(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    try:
        result = (
            client.table("merchant_users")
            .select("*, merchant_partners(*)")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except APIError as e:
        if e.code == "PGRST116":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliado no encontrado")
        raise
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliado no encontrado")
    return MerchantUserOut(**result.data)


@router.patch("/partner/{partner_id}", response_model=MerchantPartnerOut, summary="Actualizar datos del partner")
async def update_merchant_partner(
    partner_id: str,
    body: MerchantPartnerUpdate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar")
    result = (
        client.table("merchant_partners")
        .update(updates)
        .eq("id", partner_id)
        .select()
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner no encontrado")
    return MerchantPartnerOut(**result.data)


# ── Merchant: productos ───────────────────────────────────────────────────────

@router.get("/products/{partner_id}", response_model=List[MerchantProductOut], summary="Productos del partner")
async def get_products(
    partner_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_products")
        .select("*")
        .eq("merchant_partner_id", partner_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return [MerchantProductOut(**r) for r in (result.data or [])]


@router.get("/productos", response_model=List[MarketplaceProductOut], summary="Catálogo consolidado del marketplace")
async def get_marketplace_products(
    merchant_partner_id: Optional[str] = None,
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    client: Client = Depends(get_supabase_admin_client),
):
    current_time = datetime.now(timezone.utc).isoformat()
    
    query = (
        client.table("merchant_products")
        .select("*, merchant_partners!inner(*)")
        .eq("is_active", True)
        .eq("status", "active")
        .eq("merchant_partners.is_active", True)
        .lte("available_from", current_time)
        .or_(f"available_until.is.null,available_until.gte.{current_time}")
    )
    
    if merchant_partner_id:
        query = query.eq("merchant_partner_id", merchant_partner_id)
    if category:
        query = query.eq("category", category)
    if featured is not None:
        query = query.eq("featured", featured)
        
    result = query.execute()
    
    data = []
    for r in (result.data or []):
        if "merchant_partners" in r:
            r["merchant"] = r.pop("merchant_partners")
        data.append(MarketplaceProductOut(**r))
        
    return data


@router.post("/products", response_model=MerchantProductOut, status_code=status.HTTP_201_CREATED, summary="Crear producto")
async def create_product(
    body: MerchantProductCreate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    try:
        result = client.table("merchant_products").insert(body.model_dump()).execute()
        if not result.data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear el producto")
        return MerchantProductOut(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB Error: {str(e)}")


@router.patch("/products/{product_id}", response_model=MerchantProductOut, summary="Actualizar producto")
async def update_product(
    product_id: str,
    body: MerchantProductUpdate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar")
    result = (
        client.table("merchant_products")
        .update(updates)
        .eq("id", product_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return MerchantProductOut(**result.data[0])


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desactivar producto (soft delete)")
async def remove_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    client.table("merchant_products").update({"is_active": False}).eq("id", product_id).execute()


# ── Operador: perfil ──────────────────────────────────────────────────────────

@router.get("/operator/me", response_model=ValidatorOut, summary="Perfil del operador autenticado")
async def get_operator_me(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)
    try:
        result = (
            client.table("validators")
            .select("id, full_name, center_id, centers(name)")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except APIError as e:
        if e.code == "PGRST116":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operador no encontrado")
        raise
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operador no encontrado")
    return ValidatorOut(**result.data)


# ── Operador: flujo de reciclaje ──────────────────────────────────────────────

@router.post("/operator/validate-qr", response_model=ValidateQrOut, summary="Validar QR de usuario")
async def validate_qr(
    body: ValidateQrRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.rpc("validate_qr_for_operator", {
        "p_token": body.token,
        "p_validator_id": body.validator_id,
        "p_center_id": body.center_id,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR inválido")
    return ValidateQrOut(**result.data)


@router.post("/operator/delivery-session", summary="Crear sesión de entrega")
async def create_delivery_session(
    body: CreateDeliverySessionRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.rpc("create_delivery_session", {
        "p_operator_id": body.operator_id,
        "p_center_id": body.center_id,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la sesión")
    return {"session_id": result.data}


@router.post("/operator/delivery-session/item", summary="Agregar material a la sesión")
async def add_delivery_item(
    body: AddDeliveryItemRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.rpc("add_delivery_item", {
        "p_session_id": body.session_id,
        "p_material": body.material,
        "p_kg": body.kg,
    }).execute()
    return result.data


@router.delete("/operator/delivery-session/item", status_code=status.HTTP_204_NO_CONTENT, summary="Quitar material de la sesión")
async def remove_delivery_item(
    body: RemoveDeliveryItemRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    client.rpc("remove_delivery_item", {
        "p_session_id": body.session_id,
        "p_item_id": body.item_id,
    }).execute()


@router.get("/operator/delivery-session/{session_id}/summary", summary="Resumen de la sesión de entrega")
async def get_session_summary(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.rpc("get_session_summary", {"p_session_id": session_id}).execute()
    return result.data


@router.post("/operator/confirm-delivery", summary="Confirmar entrega y otorgar puntos")
async def confirm_delivery(
    body: ConfirmDeliveryRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.rpc("confirm_delivery", {
        "p_session_id": body.session_id,
        "p_qr_token": body.qr_token,
        "p_validator_id": body.validator_id,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo confirmar la entrega")
    return result.data


@router.post("/operator/register-recycling", summary="Registrar entrega individual (flujo alternativo)")
async def register_recycling(
    body: RegisterRecyclingRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = client.rpc("register_recycling_delivery", {
        "p_token": body.token,
        "p_validator_id": body.validator_id,
        "p_center_id": body.center_id,
        "p_material": body.material,
        "p_kg": body.kg,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo registrar el reciclaje")
    return result.data


# ── Banners Publicitarios ─────────────────────────────────────────────────────

@router.post("/partner/{partner_id}/banners", response_model=MerchantBannerOut, summary="Subir banner publicitario del aliado")
async def upload_partner_banner(
    partner_id: str,
    file: UploadFile = File(...),
    title: str = None,
    link_url: str = None,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    if not file.content_type.startswith("image/webp"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes en formato WebP")
    
    try:
        file_bytes = await file.read()
        file_path = f"banners/{partner_id}_{int(datetime.now(timezone.utc).timestamp())}.webp"
        
        # Upload to supabase storage
        client.storage.from_("almacenamiento").upload(file_path, file_bytes, {"content-type": "image/webp"})
        
        # Get public url
        public_url = client.storage.from_("almacenamiento").get_public_url(file_path)
        
        # Insert into merchant_banners
        banner_data = {
            "merchant_partner_id": partner_id,
            "banner_url": public_url,
            "title": title,
            "link_url": link_url,
            "is_active": True
        }
        result = client.table("merchant_banners").insert(banner_data).execute()
        
        return MerchantBannerOut(**result.data[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/partner/{partner_id}/banners", response_model=List[MerchantBannerOut], summary="Listar banners del aliado")
async def get_partner_banners(
    partner_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_banners")
        .select("*")
        .eq("merchant_partner_id", partner_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [MerchantBannerOut(**r) for r in (result.data or [])]

@router.patch("/partner/{partner_id}/banners/{banner_id}", response_model=MerchantBannerOut, summary="Actualizar banner")
async def update_partner_banner(
    partner_id: str,
    banner_id: str,
    body: MerchantBannerUpdate,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar")
        
    result = (
        client.table("merchant_banners")
        .update(updates)
        .eq("id", banner_id)
        .eq("merchant_partner_id", partner_id)
        .select()
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner no encontrado")
    return MerchantBannerOut(**result.data)

@router.delete("/partner/{partner_id}/banners/{banner_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar banner")
async def delete_partner_banner(
    partner_id: str,
    banner_id: str,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    # Opcional: Podríamos borrar el archivo de storage también
    client.table("merchant_banners").delete().eq("id", banner_id).eq("merchant_partner_id", partner_id).execute()

@router.get("/banners", summary="Obtener todos los banners activos (para estudiantes)")
async def get_active_banners(
    client: Client = Depends(get_supabase_admin_client),
):
    result = (
        client.table("merchant_banners")
        .select("*, merchant_partners!inner(business_name, website_url)")
        .eq("is_active", True)
        .execute()
    )
    
    # Flatten the result for the frontend
    banners = []
    for item in (result.data or []):
        partner = item.get("merchant_partners", {})
        banner = {
            "id": item["id"],
            "merchant_partner_id": item["merchant_partner_id"],
            "title": item["title"],
            "banner_url": item["banner_url"],
            "link_url": item["link_url"] or partner.get("website_url"), # Fallback al website general
            "business_name": partner.get("business_name"),
            "display_order": item["display_order"]
        }
        banners.append(banner)
        
    return banners

