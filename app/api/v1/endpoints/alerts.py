from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta
from app.api.deps import get_db
from app.db.models.alert import Alert
from app.db.models.floor import Floor
from app.db.models.building import Building
from app.db.models.enums import AlertStatus, AlertLevel, Variable
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
    level: Optional[AlertLevel] = Query(None, description="Filtrar por nivel: info, medium, critical"),
    variable: Optional[Variable] = Query(None, description="Filtrar por variable: temperature, humidity, energy"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Alert)
    if floor_id:
        q = q.filter(Alert.floor_id == floor_id)
    if status:
        q = q.filter(Alert.status == status)
    if level:
        q = q.filter(Alert.level == level)
    if variable:
        q = q.filter(Alert.variable == variable)
    return q.order_by(Alert.created_at.desc()).limit(limit).all()

@router.get("/by-building", response_model=List[dict])
def list_alerts_by_building(
    edificio: str,
    piso: Optional[int] = None,
    nivel: Optional[AlertLevel] = Query(None, description="info | medium | critical"),
    status: Optional[AlertStatus] = Query(None, description="open | acknowledged | closed"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Lista alertas por edificio con información del piso"""
    building = db.query(Building).filter_by(code=edificio).first()
    if not building:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")

    q = (
        db.query(Alert, Floor.number.label("piso"))
        .join(Floor, Floor.id == Alert.floor_id)
        .filter(Floor.building_id == building.id)
    )
    if piso is not None:
        q = q.filter(Floor.number == piso)
    if nivel is not None:
        q = q.filter(Alert.level == nivel)
    if status is not None:
        q = q.filter(Alert.status == status)

    rows = q.order_by(Alert.created_at.desc()).limit(limit).all()

    out = []
    for alert, piso_num in rows:
        out.append({
            "id": alert.id,
            "timestamp": alert.created_at.isoformat(),
            "piso": piso_num,
            "variable": alert.variable.value,
            "nivel": alert.level.value,
            "status": alert.status.value,
            "mensaje": alert.message,
            "recomendacion": alert.recommendation,
        })
    return out

@router.patch("/{alert_id}/status", response_model=AlertOut)
def update_alert_status(
    alert_id: int,
    status: AlertStatus,
    db: Session = Depends(get_db),
):
    """Actualiza el estado de una alerta"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    alert.status = status
    db.commit()
    db.refresh(alert)
    return alert

@router.get("/stats", response_model=dict)
def get_alert_stats(
    edificio: str,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Obtiene estadísticas de alertas"""
    building = db.query(Building).filter_by(code=edificio).first()
    if not building:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")

    since = datetime.utcnow() - timedelta(hours=hours)
    
    q = (
        db.query(Alert, Floor.number.label("piso"))
        .join(Floor, Floor.id == Alert.floor_id)
        .filter(
            Floor.building_id == building.id,
            Alert.created_at >= since
        )
    )
    
    alerts = q.all()
    
    stats = {
        "total": len(alerts),
        "por_nivel": {
            "critical": sum(1 for a, _ in alerts if a.level == AlertLevel.critical),
            "medium": sum(1 for a, _ in alerts if a.level == AlertLevel.medium),
            "info": sum(1 for a, _ in alerts if a.level == AlertLevel.info),
        },
        "por_variable": {
            "temperature": sum(1 for a, _ in alerts if a.variable == Variable.temperature),
            "humidity": sum(1 for a, _ in alerts if a.variable == Variable.humidity),
            "energy": sum(1 for a, _ in alerts if a.variable == Variable.energy),
        },
        "por_status": {
            "open": sum(1 for a, _ in alerts if a.status == AlertStatus.open),
            "acknowledged": sum(1 for a, _ in alerts if a.status == AlertStatus.acknowledged),
            "closed": sum(1 for a, _ in alerts if a.status == AlertStatus.closed),
        }
    }
    
    return stats
