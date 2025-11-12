from pydantic import BaseModel
from typing import Optional
from app.db.models.enums import Variable, AlertLevel, AlertStatus
from datetime import datetime

class AlertCreate(BaseModel):
    floor_id: int
    variable: Variable
    level: AlertLevel
    status: AlertStatus = AlertStatus.open
    message: str
    recommendation: Optional[str] = None

class AlertOut(AlertCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True
