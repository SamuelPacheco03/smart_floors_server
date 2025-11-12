from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.deps import get_db
from app.db.models.alert import Alert
from app.db.models.enums import AlertStatus
from app.db.schemas.alert import AlertCreate, AlertOut

router = APIRouter()

@router.post("/", response_model=AlertOut, status_code=201)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    obj = Alert(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/", response_model=List[AlertOut])
def list_alerts(
    floor_id: Optional[int] = None,
    status: Optional[AlertStatus] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if floor_id:
        q = q.filter(Alert.floor_id == floor_id)
    if status:
        q = q.filter(Alert.status == status)
    return q.order_by(Alert.created_at.desc()).limit(limit).all()
