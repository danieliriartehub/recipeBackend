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
    GenerateProductDetailsRequest,
    GenerateProductDetailsOut,
    AdTrackingRequest,
)

import os
import google.generativeai as genai
import json
import random

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

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


# ── IA Generativa: Detalles de Producto ───────────────────────────────────────

@router.post("/generate-product-details", response_model=GenerateProductDetailsOut, summary="Genera descripción y categoría con IA")
async def generate_product_details(
    payload: GenerateProductDetailsRequest,
    current_user: dict = Depends(get_current_user)
):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Eres un experto en marketing y ventas para RECIPE, una plataforma de reciclaje donde estudiantes universitarios canjean "Puntos ECO" por productos ecológicos y beneficios.
        
        El aliado comercial quiere registrar un nuevo producto llamado: "{payload.name}".
        
        Tu tarea es:
        1. Redactar una descripción muy atractiva, persuasiva y corta (máximo 2-3 líneas) para este producto, enfocándote en el público universitario. Usa algún emoji.
        2. Inferir a qué categoría pertenece. Las categorías recomendadas son: Alimentos, Merchandising, Servicios, Hogar y Eco, General. Si no encaja, crea una corta.

        Debes responder ÚNICAMENTE con un objeto JSON con este formato exacto, sin markdown ni bloques de código:
        {{
            "description": "Tu descripción aquí",
            "category": "Tu categoría aquí"
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        data = json.loads(text.strip())
        return GenerateProductDetailsOut(
            description=data.get("description", "Descripción generada automáticamente"),
            category=data.get("category", "General")
        )
    except Exception as e:
        print(f"Error generando detalles con IA: {e}")
        # Fallback si falla la IA o no hay API key configurada
        return GenerateProductDetailsOut(
            description=f"El producto perfecto para tus necesidades: {payload.name}.",
            category="General"
        )


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
    client: Client = Depends(get_supabase_admin_client)
):
    try:
        result = (
            client.table("merchant_banners")
            .select("*, merchant_partners(id, business_name, is_active, website_url)")
            .eq("is_active", True)
            .execute()
        )
    except APIError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
    banners = []
    for row in result.data:
        partner = row.get("merchant_partners")
        if partner and partner.get("is_active"):
            banner = {k: v for k, v in row.items() if k != "merchant_partners"}
            banner["business_name"] = partner.get("business_name")
            banner["link_url"] = banner.get("link_url") or partner.get("website_url")
            banners.append(banner)
            
    return banners


# ── ML Ad Targeting ───────────────────────────────────────────────────────────

@router.post("/banners/track", summary="Registra vistas o clics de un banner para ML")
async def track_banner(
    payload: AdTrackingRequest,
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client)
):
    if payload.action not in ["view", "click"]:
        raise HTTPException(status_code=400, detail="Action must be view or click")
    
    try:
        data = {
            "user_id": current_user.id,
            "banner_id": payload.banner_id,
            "action": payload.action
        }
        client.table("ad_analytics").insert(data).execute()
        return {"success": True}
    except Exception as e:
        print(f"Error tracking banner: {e}")
        # Silently fail so it doesn't break the frontend experience
        return {"success": False, "error": str(e)}

@router.get("/banners/target", response_model=MerchantBannerOut, summary="Motor de ML (Epsilon-Greedy) para elegir el mejor banner")
async def get_targeted_banner(
    current_user: dict = Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client)
):
    try:
        # 1. Obtener todos los banners activos
        result = client.table("merchant_banners").select("*, merchant_partners(id, business_name, is_active, website_url)").eq("is_active", True).execute()
        
        banners = []
        for row in result.data:
            partner = row.get("merchant_partners")
            if partner and partner.get("is_active"):
                banner = {k: v for k, v in row.items() if k != "merchant_partners"}
                banner["business_name"] = partner.get("business_name")
                banner["link_url"] = banner.get("link_url") or partner.get("website_url")
                banners.append(banner)
        
        if not banners:
            raise HTTPException(status_code=404, detail="No active banners found")

        # 2. Algoritmo Epsilon-Greedy
        EPSILON = 0.3 # 30% de las veces explora (random)
        
        if random.random() < EPSILON:
            # EXPLORACIÓN: Elegir uno al azar
            selected = random.choice(banners)
            selected['is_ml_targeted'] = False
            return selected
            
        # 3. EXPLOTACIÓN: Buscar el banner con mejor CTR histórico
        analytics_res = client.table("ad_analytics").select("banner_id, action").execute()
        analytics = analytics_res.data
        
        if not analytics:
            selected = random.choice(banners)
            selected['is_ml_targeted'] = False
            return selected
            
        # Calcular CTR por banner
        stats = {}
        for row in analytics:
            b_id = row['banner_id']
            act = row['action']
            if b_id not in stats:
                stats[b_id] = {"views": 0, "clicks": 0}
            if act == "view":
                stats[b_id]["views"] += 1
            elif act == "click":
                stats[b_id]["clicks"] += 1
                
        best_banner_id = None
        best_ctr = -1
        
        for b_id, metrics in stats.items():
            views = metrics["views"]
            clicks = metrics["clicks"]
            ctr = clicks / views if views > 0 else 0
            if ctr > best_ctr:
                best_ctr = ctr
                best_banner_id = b_id
                
        # Encontrar el banner con best_banner_id
        selected = next((b for b in banners if b['id'] == best_banner_id), random.choice(banners))
        selected['is_ml_targeted'] = True
        return selected

    except Exception as e:
        print(f"Error in ML targeting: {e}")
        # Fallback de seguridad: devolver el primero o uno random si falla
        banners_res = client.table("merchant_banners").select("*").eq("is_active", True).execute()
        if banners_res.data:
            selected = random.choice(banners_res.data)
            selected['is_ml_targeted'] = False
            return selected
        raise HTTPException(status_code=500, detail="Internal server error")
