from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class CreateSessionResponse(BaseModel):
    formToken: str
    orderId: str



