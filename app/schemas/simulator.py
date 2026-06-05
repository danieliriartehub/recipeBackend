from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal


class MaterialOut(BaseModel):
    type: str
    label: str
    emoji: Optional[str] = ""
    points_per_kg: int = 0
    co2_per_kg: float = 0.0
    trees_equivalent_per_kg: float = 0.0

    # Convierte Decimal / string proveniente de Supabase a float limpio
    @field_validator("co2_per_kg", "trees_equivalent_per_kg", mode="before")
    @classmethod
    def coerce_to_float(cls, v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
