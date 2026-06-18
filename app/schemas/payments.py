from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SubscriptionOut(BaseModel):
    id: str
    user_id: str
    status: str
    plan: str
    amount_soles: float
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class IzipayWebhookPayload(BaseModel):
    """
    Payload que IziPay envía al webhook tras un pago.
    Campos clave según la documentación oficial de IziPay Perú.
    """
    orderStatus: Optional[str] = None
    orderId: Optional[str] = None
    uuid: Optional[str] = None
    # IziPay puede enviar campos adicionales — usamos model_config extra='allow'
    model_config = {"extra": "allow"}
