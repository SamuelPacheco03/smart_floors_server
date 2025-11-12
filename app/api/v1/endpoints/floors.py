from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.db.models.floor import Floor
from app.db.schemas.floor import FloorCreate, FloorOut

router = APIRouter()

@router.get("/", response_model=List[FloorOut])
def list_floors(db: Session = Depends(get_db)):
    return db.query(Floor).order_by(Floor.id).all()

@router.post("/", response_model=FloorOut, status_code=201)
def create_floor(payload: FloorCreate, db: Session = Depends(get_db)):
    obj = Floor(**payload.model_dump())
    db.add(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error creando piso (¿duplicado de nombre por edificio?)")
    db.refresh(obj)
    return obj
