from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from app.db.models.enums import Variable


class ThresholdBase(BaseModel):
    floor_id: int
    variable: Variable
    lower: Decimal
    upper: Decimal
    is_active: bool = True


class ThresholdCreate(ThresholdBase):
    pass


class ThresholdOut(ThresholdBase):
    id: int

    class Config:
        from_attributes = True
