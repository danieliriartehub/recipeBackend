from pydantic import BaseModel
from decimal import Decimal


class MaterialOut(BaseModel):
    type: str
    label: str
    emoji: str
    points_per_kg: int
    co2_per_kg: Decimal
    trees_equivalent_per_kg: Decimal
