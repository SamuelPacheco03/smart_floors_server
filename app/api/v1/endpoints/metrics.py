from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.api.deps import get_db
from app.db.models.metric import Metric
from app.db.schemas.metric import MetricCreate, MetricOut

router = APIRouter()

@router.post("/", response_model=MetricOut, status_code=201)
def ingest_metric(payload: MetricCreate, db: Session = Depends(get_db)):
    obj = Metric(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/", response_model=List[MetricOut])
def list_metrics(
    floor_id: int,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    q = db.query(Metric).filter(Metric.floor_id == floor_id)
    if since:
        q = q.filter(Metric.time >= since)
    if until:
        q = q.filter(Metric.time <= until)
    return q.order_by(Metric.time.desc()).limit(limit).all()
