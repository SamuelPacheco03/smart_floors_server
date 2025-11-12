from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal


class MetricCreate(BaseModel):
    time: datetime
    floor_id: int
    temp_c: Optional[Decimal] = None
    humidity_pct: Optional[Decimal] = None
    energy_kw: Optional[Decimal] = None


class MetricOut(MetricCreate):
    id: int

    class Config:
        from_attributes = True
