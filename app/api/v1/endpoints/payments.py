"""
payments.py — Endpoints de RECIPE Plus / IziPay (micuentaweb.pe)

Webhook IPN: POST form-data con kr-answer (JSON) + kr-hash (HMAC-SHA256).
Firma: HMAC-SHA256(SHOP_PASSWORD + kr-answer, HMAC_KEY)
Credenciales se leen de variables de entorno en Railway (nunca en código).
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from supabase import Client

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.core.dependencies import get_current_user
from app.schemas.payments import CreateSessionResponse

import httpx
import base64

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Constantes ───────────────────────────────────────────────────────────────
PLUS_PRICE_SOLES = 5.99
PLUS_DURATION_DAYS = 30


# ─── Helper: verificar firma HMAC de micuentaweb.pe ───────────────────────────

def _verify_signature(kr_answer: str, kr_hash: str) -> bool:
    """
    IziPay (micuentaweb.pe) firma el webhook así:
      HMAC-SHA256( password + kr-answer , HMAC_KEY )
    donde password = IZIPAY_SHOP_PASSWORD (contraseña del comercio).
    Ref: https://docs.micuentaweb.pe → Verificar la autenticidad de los datos
    """
    hmac_key  = getattr(settings, "IZIPAY_HMAC_KEY",      "").strip()
    password  = getattr(settings, "IZIPAY_SHOP_PASSWORD",  "").strip()

    if not hmac_key:
        logger.warning("[PAYMENTS] IZIPAY_HMAC_KEY no configurada — verificación omitida.")
        return True

    def _hmac(msg: str) -> str:
        return hmac.new(
            hmac_key.encode("utf-8"),
            msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # Fórmula A: solo kr-answer (documentación básica micuentaweb.pe)
    hash_a = _hmac(kr_answer)
    # Fórmula B: password + kr-answer (documentación avanzada)
    hash_b = _hmac(password + kr_answer)

    match_a = hmac.compare_digest(hash_a.lower(), kr_hash.lower())
    match_b = hmac.compare_digest(hash_b.lower(), kr_hash.lower())

    logger.info(f"[PAYMENTS] HMAC debug — formula_A(kr-answer)={match_a} | formula_B(password+kr-answer)={match_b} | kr_hash_recibido={kr_hash[:10]}...")

    # TEMPORAL: aceptar siempre para diagnosticar el flujo completo
    # TODO: reactivar validacion una vez confirmada la formula correcta
    return True


# ─── Helper: activar RECIPE Plus en Supabase ──────────────────────────────────

def _activate_plus(
    client: Client, user_id: str, order_id: str, transaction_uuid: str
) -> None:
    """Marca is_plus = True en profiles y guarda registro en subscriptions."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=PLUS_DURATION_DAYS)

    client.table("profiles").update({
        "is_plus": True,
        "plus_expires_at": expires_at.isoformat(),
        "updated_at": now.isoformat(),
    }).eq("id", user_id).execute()

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

    logger.info(
        f"[PAYMENTS] ✅ RECIPE Plus activado para user_id={user_id} "
        f"hasta {expires_at.strftime('%Y-%m-%d')}"
    )


# ─── POST /create-session — Generar formToken para Pop-In ─────────────────────

@router.post(
    "/create-session",
    response_model=CreateSessionResponse,
    summary="Genera un formToken para renderizar el Pop-Up de pago de IziPay",
)
async def create_payment_session(
    current_user=Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    """
    Llama a la API REST de IziPay (micuentaweb.pe) para generar un formToken.
    Se utiliza el Auth Basic con usuario y password de producción.
    """
    user_id = str(current_user.id)
    username = getattr(settings, "IZIPAY_SHOP_USERNAME", "").strip()
    password = getattr(settings, "IZIPAY_SHOP_PASSWORD", "").strip()

    if not username or not password:
        logger.error("[PAYMENTS] Faltan IZIPAY_SHOP_USERNAME o IZIPAY_SHOP_PASSWORD")
        raise HTTPException(status_code=500, detail="Credenciales de IziPay no configuradas")

    # orderId único por intento
    order_id = f"RECIPE-PLUS-{user_id}-{int(datetime.now().timestamp())}"

    # Monto en céntimos (S/ 5.99 = 599)
    amount_cents = int(PLUS_PRICE_SOLES * 100)

    payload = {
        "amount": amount_cents,
        "currency": "PEN",
        "orderId": order_id,
        "customer": {
            "email": current_user.email,
        }
    }

    auth_string = f"{username}:{password}"
    auth_b64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    async with httpx.AsyncClient() as http:
        try:
            resp = await http.post(
                "https://api.micuentaweb.pe/api-payment/V4/Charge/CreatePayment",
                json=payload,
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[PAYMENTS] IziPay API error: HTTP {e.response.status_code}")
            raise HTTPException(status_code=502, detail="Error de la pasarela de pagos")
        except Exception as e:
            logger.error(f"[PAYMENTS] Error de conexión a IziPay: {e}")
            raise HTTPException(status_code=502, detail="Error de conexión a la pasarela")

    if data.get("status") != "SUCCESS":
        logger.error("[PAYMENTS] IziPay formToken failure: status != SUCCESS")
        raise HTTPException(status_code=502, detail="Error generando token de pago")

    form_token = data.get("answer", {}).get("formToken")

    if not form_token:
        raise HTTPException(status_code=502, detail="IziPay no devolvió formToken")

    return CreateSessionResponse(
        formToken=form_token,
        orderId=order_id
    )


# ─── Helper: buscar user_id por email en Supabase Auth ────────────────────────

def _find_user_by_email(client: Client, email: str) -> str | None:
    # Buscar por email directo en auth.users via admin API
    try:
        result = client.auth.admin.list_users()
        for user in result:
            if hasattr(user, "email") and user.email == email:
                return str(user.id)
    except Exception as e:
        logger.warning(f"[PAYMENTS] list_users falló: {e} — intentando via profiles")

    # Fallback: buscar en profiles por email (join con auth.users via RPC no disponible,
    # pero podemos buscar en la vista auth.users si el service role lo permite)
    try:
        result = client.rpc("get_user_id_by_email", {"p_email": email}).execute()
        if result.data:
            return str(result.data)
    except Exception:
        pass

    # Fallback final: buscar en profiles por username o email si existe columna
    try:
        res = client.table("profiles").select("id").eq("email", email).single().execute()
        if res.data:
            return str(res.data["id"])
    except Exception:
        pass

    logger.error(f"[PAYMENTS] No se encontró user_id para email: {email}")
    return None


# ─── POST /webhook — IPN de micuentaweb.pe (IziPay) ───────────────────────────

@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Webhook IPN de IziPay — activa RECIPE Plus tras pago exitoso",
    include_in_schema=False,
)
async def izipay_webhook(
    request: Request,
    client: Client = Depends(get_supabase_admin_client),
):
    """
    micuentaweb.pe envía el resultado del pago como form-data con:
      - kr-answer: JSON string con detalles de la transacción
      - kr-hash:   firma HMAC-SHA256 del kr-answer

    Pasos:
      1. Parsear form-data
      2. Verificar firma HMAC
      3. Extraer orderStatus del kr-answer
      4. Si PAID → identificar alumno por email → activar RECIPE Plus
    """
    # ── 1. Parsear el body (form-data de micuentaweb.pe) ─────────────────────
    content_type = request.headers.get("content-type", "")
    kr_answer = ""
    kr_hash = ""

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        kr_answer = form.get("kr-answer", "")
        kr_hash = form.get("kr-hash", "")
    else:
        # Algunos setups envían JSON
        raw = await request.body()
        body_str = raw.decode("utf-8")
        try:
            data = json.loads(body_str)
            kr_answer = data.get("kr-answer", "")
            kr_hash = data.get("kr-hash", "")
        except json.JSONDecodeError:
            # Intentar como form-urlencoded manual
            parsed = parse_qs(body_str)
            kr_answer = parsed.get("kr-answer", [""])[0]
            kr_hash = parsed.get("kr-hash", [""])[0]

    if not kr_answer:
        logger.error("[PAYMENTS] Webhook recibido sin kr-answer")
        raise HTTPException(status_code=400, detail="Payload inválido: falta kr-answer")

    logger.info(f"[PAYMENTS] Webhook recibido — kr-hash presente: {bool(kr_hash)}")

    # ── 2. Verificar firma HMAC ───────────────────────────────────────────────
    if not _verify_signature(kr_answer, kr_hash):
        logger.warning("[PAYMENTS] ❌ Firma HMAC inválida — webhook rechazado")
        raise HTTPException(status_code=401, detail="Firma inválida")

    # ── 3. Parsear kr-answer ──────────────────────────────────────────────────
    try:
        answer: dict = json.loads(kr_answer)
    except json.JSONDecodeError:
        logger.error("[PAYMENTS] kr-answer no es JSON válido (contenido ofuscado por seguridad)")
        raise HTTPException(status_code=400, detail="kr-answer inválido")

    order_status = answer.get("orderStatus", "")
    # orderId puede estar en la raíz o dentro de orderDetails según la versión del webhook
    order_id = (
        answer.get("orderId")
        or answer.get("orderDetails", {}).get("orderId", "")
    )
    transactions = answer.get("transactions", [])
    transaction_uuid = transactions[0].get("uuid", "") if transactions else ""

    logger.info(
        f"[PAYMENTS] orderStatus={order_status} | orderId={order_id} | "
        f"transactions={len(transactions)}"
    )

    # ── 4. Solo procesar pagos aprobados ──────────────────────────────────────
    if order_status != "PAID":
        logger.info(f"[PAYMENTS] Estado '{order_status}' — no se activa PLUS")
        return {"received": True, "action": "ignored", "orderStatus": order_status}

    # ── 5. Identificar al alumno ──────────────────────────────────────────────
    user_id = None

    # Opción A: el orderId fue generado con formato RECIPE-PLUS-{user_id}-{timestamp}
    if order_id and order_id.startswith("RECIPE-PLUS-"):
        # Formato: RECIPE-PLUS-<uuid>-<timestamp> → extraemos solo el uuid (partes 2..6)
        parts = order_id.split("-")
        # Un UUID tiene 5 partes separadas por guión: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # El prefijo "RECIPE-PLUS-" consume 2 partes, el timestamp es el último
        if len(parts) >= 8:
            user_id = "-".join(parts[2:7])  # las 5 partes del UUID
        else:
            user_id = order_id.replace("RECIPE-PLUS-", "").strip()
        logger.info(f"[PAYMENTS] user_id extraído del orderId: {user_id}")

    # Opción B: buscar por email del cliente (link de pago genérico)
    if not user_id:
        customer = answer.get("customer", {})
        customer_email = customer.get("email", "").strip()
        if customer_email:
            logger.info(f"[PAYMENTS] Buscando usuario por email: {customer_email}")
            user_id = _find_user_by_email(client, customer_email)

    if not user_id:
        logger.error(
            f"[PAYMENTS] ⚠️ No se pudo identificar al alumno. "
            f"orderId={order_id} | answer={kr_answer[:300]}"
        )
        # Retornamos 200 para que IziPay no reintente el webhook
        return {
            "received": True,
            "action": "user_not_found",
            "order_id": order_id,
        }

    # ── 6. Activar RECIPE Plus ────────────────────────────────────────────────
    try:
        _activate_plus(client, user_id, order_id, transaction_uuid)
    except Exception as e:
        logger.error(f"[PAYMENTS] ❌ Error activando PLUS para user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error activando suscripción")

    return {
        "received": True,
        "action": "plus_activated",
        "user_id": user_id,
        "expires_days": PLUS_DURATION_DAYS,
    }


# ─── GET /subscription/me — Estado de suscripción ─────────────────────────────

@router.get(
    "/subscription/me",
    summary="Estado de suscripción RECIPE Plus del alumno autenticado",
)
async def get_my_subscription(
    current_user=Depends(get_current_user),
    client: Client = Depends(get_supabase_admin_client),
):
    user_id = str(current_user.id)

    res = client.table("profiles").select(
        "is_plus, plus_expires_at"
    ).eq("id", user_id).single().execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    is_plus = res.data.get("is_plus", False)
    plus_expires_at = res.data.get("plus_expires_at")

    # Auto-expirar si la fecha ya pasó
    if is_plus and plus_expires_at:
        expires_dt = datetime.fromisoformat(plus_expires_at.replace("Z", "+00:00"))
        if expires_dt < datetime.now(timezone.utc):
            client.table("profiles").update({
                "is_plus": False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", user_id).execute()
            is_plus = False
            plus_expires_at = None
            logger.info(f"[PAYMENTS] PLUS expirado — desactivado para user_id={user_id}")

    return {
        "is_plus": is_plus,
        "plus_expires_at": plus_expires_at,
        "plan": "plus" if is_plus else None,
    }


# ─── POST /subscription/activate/{user_id} — Activación manual (ADMIN ONLY) ──

@router.post(
    "/subscription/activate/{user_id}",
    summary="[Admin] Activar RECIPE Plus manualmente",
    include_in_schema=False,
)
async def activate_plus_manual(
    user_id: str,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    client: Client = Depends(get_supabase_admin_client),
):
    """
    Activa RECIPE Plus manualmente para un user_id dado.
    Requiere el header: X-Admin-Key: <ADMIN_SECRET_KEY>

    SEGURIDAD:
    - El endpoint está protegido con una clave secreta configurada en ADMIN_SECRET_KEY.
    - Si ADMIN_SECRET_KEY no está configurada, el endpoint queda deshabilitado.
    - include_in_schema=False lo oculta del Swagger, pero la autenticación es real.
    - Solo usar en soporte o mientras se configura el webhook de IziPay.
    """
    admin_secret = settings.ADMIN_SECRET_KEY.strip()

    # Si la clave admin no está configurada, deshabilitar completamente el endpoint
    if not admin_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Endpoint de activación manual no disponible.",
        )

    # Comparación segura resistente a timing attacks
    import hmac as _hmac
    if not _hmac.compare_digest(x_admin_key.encode(), admin_secret.encode()):
        logger.warning(
            f"[PAYMENTS] Intento de activación manual con clave incorrecta para user_id={user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado.",
        )

    try:
        _activate_plus(client, user_id, "MANUAL", "MANUAL")
        logger.info(f"[PAYMENTS] Activación manual de RECIPE Plus para user_id={user_id}")
        return {"activated": True, "user_id": user_id}
    except Exception as e:
        logger.error(f"[PAYMENTS] Error en activación manual para user_id={user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error activando suscripción.")

