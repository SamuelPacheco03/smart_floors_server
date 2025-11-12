from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.db.models.building import Building
from app.db.schemas.building import BuildingCreate, BuildingOut

router = APIRouter()

@router.get("/", response_model=List[BuildingOut])
def list_buildings(db: Session = Depends(get_db)):
    return db.query(Building).order_by(Building.id).all()

@router.post("/", response_model=BuildingOut, status_code=201)
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)):
    obj = Building(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
