from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class MetricIn(BaseModel):
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    edificio: str
    piso: int
    temp_C: Optional[Decimal] = None
    humedad_pct: Optional[Decimal] = None
    energia_kW: Optional[Decimal] = None


class MetricInBatch(BaseModel):
    items: List[MetricIn]
