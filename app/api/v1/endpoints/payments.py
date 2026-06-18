"""
payments.py — Endpoints de RECIPE Plus / IziPay

Flujo con Link de Pago:
  1. El alumno paga en la página alojada de IziPay
  2. IziPay hace POST a /api/v1/payments/webhook con el resultado
  3. Este endpoint verifica la firma HMAC-SHA256 y activa is_plus en Supabase

Endpoint adicional:
  GET /api/v1/payments/subscription/me — devuelve el estado de suscripción
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from supabase import Client

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.payments import SubscriptionOut

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Constantes ──────────────────────────────────────────────────────────────
PLUS_PRICE_SOLES = 5.99
PLUS_DURATION_DAYS = 30


# ─── Helper: verificar firma HMAC de IziPay ──────────────────────────────────

def _verify_izipay_signature(payload_str: str, received_signature: str) -> bool:
    """
    IziPay firma el cuerpo del webhook con HMAC-SHA256 usando la clave HMAC
    del comercio. Verificamos que el hash coincida antes de procesar el pago.

    Si IZIPAY_HMAC_KEY no está configurada (durante desarrollo / sin credenciales),
    se omite la verificación y se loguea una advertencia.
    """
    hmac_key = getattr(settings, "IZIPAY_HMAC_KEY", None)

    if not hmac_key:
        logger.warning(
            "[PAYMENTS] IZIPAY_HMAC_KEY no configurada — "
            "verificación de firma omitida. Configura la variable en Railway."
        )
        return True  # Permisivo hasta tener las credenciales reales

    expected = hmac.new(
        hmac_key.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, received_signature)


# ─── Helper: activar RECIPE Plus en Supabase ─────────────────────────────────

def _activate_plus(client: Client, user_id: str, order_id: str, transaction_uuid: str) -> None:
    """Actualiza profiles y crea/actualiza registro en subscriptions."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=PLUS_DURATION_DAYS)

    # 1. Actualizar profiles
    client.table("profiles").update({
        "is_plus": True,
        "plus_expires_at": expires_at.isoformat(),
        "updated_at": now.isoformat(),
    }).eq("id", user_id).execute()

    # 2. Registrar en subscriptions (historial)
    client.table("subscriptions").upsert({
        "user_id": user_id,
        "status": "active",
        "plan": "plus",
        "amount_soles": PLUS_PRICE_SOLES,
        "izipay_order_id": order_id,
        "izipay_transaction_uuid": transaction_uuid,
        "starts_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "updated_at": now.isoformat(),
    }, on_conflict="user_id").execute()

    logger.info(f"[PAYMENTS] RECIPE Plus activado para user_id={user_id} hasta {expires_at.date()}")


# ─── POST /webhook — Callback de IziPay ──────────────────────────────────────

@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Webhook IziPay — activa RECIPE Plus tras pago exitoso",
    include_in_schema=False,  # Ocultar de docs públicas por seguridad
)
async def izipay_webhook(
    request: Request,
    client: Client = Depends(get_supabase_admin_client),
):
    """
    IziPay realiza un POST a este endpoint cuando el pago es procesado.
    Verifica la firma HMAC y activa is_plus en el perfil del alumno.

    El orderId debe seguir el formato: RECIPE-PLUS-{user_id}
    (lo configuras al crear el link de pago en el dashboard de IziPay)
    """
    raw_body = await request.body()
    payload_str = raw_body.decode("utf-8")

    # ── 1. Verificar firma HMAC ──────────────────────────────────────────────
    signature = request.headers.get("kr-hash", "") or request.headers.get("x-izipay-signature", "")
    if not _verify_izipay_signature(payload_str, signature):
        logger.warning("[PAYMENTS] Firma HMAC inválida — webhook rechazado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma inválida",
        )

    # ── 2. Parsear el payload ────────────────────────────────────────────────
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload inválido",
        )

    order_status = data.get("orderStatus") or data.get("kr-answer", {}).get("orderStatus", "")
    order_id = data.get("orderId") or data.get("kr-answer", {}).get("orderId", "")
    transaction_uuid = data.get("uuid") or data.get("kr-answer", {}).get("transactions", [{}])[0].get("uuid", "")

    logger.info(f"[PAYMENTS] Webhook recibido — orderStatus={order_status} orderId={order_id}")

    # ── 3. Solo procesar pagos aprobados ────────────────────────────────────
    if order_status != "PAID":
        logger.info(f"[PAYMENTS] Estado no es PAID ({order_status}) — ignorando")
        return {"received": True, "action": "ignored"}

    # ── 4. Extraer user_id del orderId ──────────────────────────────────────
    # Formato esperado: RECIPE-PLUS-{user_id}
    # Si usas el link genérico de IziPay, el orderId viene del sistema de ellos.
    # En ese caso, busca el email del comprador en el payload para mapear.
    user_id = None

    if order_id and order_id.startswith("RECIPE-PLUS-"):
        user_id = order_id.replace("RECIPE-PLUS-", "")
    else:
        # Intentar extraer email del cliente desde el payload de IziPay
        customer_email = (
            data.get("customer", {}).get("email")
            or data.get("kr-answer", {}).get("customer", {}).get("email")
        )
        if customer_email:
            # Buscar user_id en Supabase por email
            res = client.table("profiles").select("id").eq(
                "id",
                client.auth.admin.get_user_by_email(customer_email).user.id
                if customer_email else None
            ).execute()
            if res.data:
                user_id = res.data[0]["id"]

    if not user_id:
        logger.error(f"[PAYMENTS] No se pudo identificar al usuario para orderId={order_id}")
        # Retornamos 200 para que IziPay no reintente, pero logueamos el error
        return {"received": True, "action": "user_not_found", "order_id": order_id}

    # ── 5. Activar RECIPE Plus ───────────────────────────────────────────────
    try:
        _activate_plus(client, user_id, order_id, transaction_uuid)
    except Exception as e:
        logger.error(f"[PAYMENTS] Error activando PLUS para user_id={user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error activando suscripción",
        )

    return {"received": True, "action": "plus_activated", "user_id": user_id}


# ─── GET /subscription/me — Estado de suscripción del alumno ─────────────────

@router.get(
    "/subscription/me",
    summary="Estado de suscripción RECIPE Plus del alumno autenticado",
)
async def get_my_subscription(
    current_user=Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    """
    Devuelve si el alumno tiene RECIPE Plus activo y cuándo expira.
    El frontend usa este endpoint para mostrar el badge ACTIVO en el perfil.
    """
    user_id = str(current_user.id)

    profile_res = client.table("profiles").select(
        "is_plus, plus_expires_at"
    ).eq("id", user_id).single().execute()

    if not profile_res.data:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    is_plus = profile_res.data.get("is_plus", False)
    plus_expires_at = profile_res.data.get("plus_expires_at")

    # Auto-expirar si ya pasó la fecha
    if is_plus and plus_expires_at:
        expires_dt = datetime.fromisoformat(plus_expires_at.replace("Z", "+00:00"))
        if expires_dt < datetime.now(timezone.utc):
            # Desactivar automáticamente
            client.table("profiles").update({
                "is_plus": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", user_id).execute()
            is_plus = False
            logger.info(f"[PAYMENTS] PLUS expirado y desactivado para user_id={user_id}")

    return {
        "is_plus": is_plus,
        "plus_expires_at": plus_expires_at,
        "plan": "plus" if is_plus else None,
    }


# ─── POST /subscription/activate — Activación manual (solo admin/debug) ──────

@router.post(
    "/subscription/activate/{user_id}",
    summary="[Admin] Activar RECIPE Plus manualmente para un usuario",
    include_in_schema=False,
)
async def activate_plus_manual(
    user_id: str,
    client: Client = Depends(get_supabase_admin_client),
):
    """
    Endpoint de emergencia para activar RECIPE Plus manualmente desde Supabase
    o desde una herramienta de admin, sin pasar por el webhook de IziPay.
    NO requiere auth para facilitar activaciones manuales tras verificar pago.
    IMPORTANTE: Proteger con API Key antes de producción final.
    """
    try:
        _activate_plus(client, user_id, "MANUAL", "MANUAL")
        return {"activated": True, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
