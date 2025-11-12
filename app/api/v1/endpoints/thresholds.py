from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.db.models.threshold import Threshold
from app.db.schemas.threshold import ThresholdCreate, ThresholdOut

router = APIRouter()

@router.get("/", response_model=List[ThresholdOut])
def list_thresholds(db: Session = Depends(get_db)):
    return db.query(Threshold).all()

@router.post("/", response_model=ThresholdOut, status_code=201)
def create_threshold(payload: ThresholdCreate, db: Session = Depends(get_db)):
    if payload.lower > payload.upper:
        raise HTTPException(status_code=400, detail="lower no puede ser mayor que upper")
    obj = Threshold(**payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un umbral activo para esa variable y piso")
    db.refresh(obj)
    return obj
