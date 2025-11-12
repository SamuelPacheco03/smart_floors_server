from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import csv
import io

from app.api.deps import get_db
from app.db.models.metric import Metric
from app.db.models.floor import Floor
from app.db.models.building import Building
from app.db.schemas.metric import MetricIn, MetricInBatch

router = APIRouter()


# ============================================================
# 🔧 Helpers
# ============================================================

def _get_or_create_building(db: Session, code: str = "A") -> Building:
    """Busca o crea un edificio por su code (ej: 'A')."""
    building = db.query(Building).filter_by(code=code).first()
    if not building:
        building = Building(code=code)
        db.add(building)
        db.commit()
        db.refresh(building)
    return building


def _get_or_create_floor(db: Session, building: Building, floor_number: int) -> Floor:
    """Busca o crea un piso dentro de un edificio."""
    floor = (
        db.query(Floor)
        .filter(Floor.building_id == building.id, Floor.number == floor_number)
        .first()
    )
    if not floor:
        floor = Floor(number=floor_number, name=f"Piso {floor_number}", building_id=building.id)
        db.add(floor)
        db.commit()
        db.refresh(floor)
    return floor


# ============================================================
# 🧩 Ingesta de métricas vía JSON
# ============================================================

@router.post("/ingest", status_code=201)
def ingest_metrics_json(payload: MetricIn | MetricInBatch, db: Session = Depends(get_db)):
    """
    Recibe una o varias métricas.
    Formato:
    {
      "timestamp": "...",
      "edificio": "A",
      "piso": 1,
      "temp_C": 23.5,
      "humedad_pct": 51.2,
      "energia_kW": 3.8
    }
    o bien:
    {
      "items": [ ... ]
    }
    """
    items: List[MetricIn] = payload.items if isinstance(payload, MetricInBatch) else [payload]

    if not items:
        raise HTTPException(status_code=400, detail="No hay registros para ingresar")

    to_insert: list[Metric] = []

    for it in items:
        building = _get_or_create_building(db, code=it.edificio)
        floor = _get_or_create_floor(db, building, it.piso)

        m = Metric(
            time=it.timestamp,
            floor_id=floor.id,
            temp_c=it.temp_C,
            humidity_pct=it.humedad_pct,
            energy_kw=it.energia_kW,
        )
        to_insert.append(m)

    db.bulk_save_objects(to_insert)
    db.commit()

    return {
        "ingested": len(to_insert),
        "first_ts": str(min(i.timestamp for i in items)),
        "last_ts": str(max(i.timestamp for i in items)),
        "buildings": sorted({i.edificio for i in items}),
    }


# ============================================================
# 📂 Ingesta CSV
# ============================================================

@router.post("/upload-csv", status_code=201)
async def upload_metrics_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Sube un CSV con encabezado:
    timestamp,edificio,piso,temp_C,humedad_pct,energia_kW
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    expected = {"timestamp", "edificio", "piso", "temp_C", "humedad_pct", "energia_kW"}
    if set(reader.fieldnames or []) != expected:
        raise HTTPException(
            status_code=400,
            detail=f"Encabezado esperado: {','.join(sorted(expected))}"
        )

    rows: list[Metric] = []
    count = 0
    min_ts: datetime | None = None
    max_ts: datetime | None = None

    for r in reader:
        try:
            ts_raw = r["timestamp"].strip().replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_raw)
        except Exception:
            raise HTTPException(status_code=400, detail=f"timestamp inválido: {r['timestamp']}")

        edificio = (r["edificio"] or "A").strip()
        piso = int(r["piso"])

        building = _get_or_create_building(db, code=edificio)
        floor = _get_or_create_floor(db, building, piso)

        metric = Metric(
            time=ts,
            floor_id=floor.id,
            temp_c=float(r["temp_C"]) if r["temp_C"] else None,
            humidity_pct=float(r["humedad_pct"]) if r["humedad_pct"] else None,
            energy_kw=float(r["energia_kW"]) if r["energia_kW"] else None,
        )

        rows.append(metric)
        count += 1
        min_ts = ts if (min_ts is None or ts < min_ts) else min_ts
        max_ts = ts if (max_ts is None or ts > max_ts) else max_ts

    if not rows:
        raise HTTPException(status_code=400, detail="CSV vacío")

    db.bulk_save_objects(rows)
    db.commit()

    return {
        "ingested": count,
        "first_ts": str(min_ts),
        "last_ts": str(max_ts),
        "buildings": "creados o actualizados dinámicamente",
    }


# ============================================================
# 🔍 Consulta de métricas
# ============================================================

@router.get("/", summary="Listar métricas por edificio y piso", response_model=list[dict])
def list_metrics(
    edificio: str,
    piso: int,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """
    Devuelve métricas filtradas por edificio y piso.
    Ejemplo:
    /metrics?edificio=A&piso=2&limit=100
    """
    building = db.query(Building).filter_by(code=edificio).first()
    if not building:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")

    floor = (
        db.query(Floor)
        .filter(Floor.building_id == building.id, Floor.number == piso)
        .first()
    )
    if not floor:
        raise HTTPException(status_code=404, detail="Piso no encontrado")

    q = db.query(Metric).filter(Metric.floor_id == floor.id)
    if since:
        q = q.filter(Metric.time >= since)
    if until:
        q = q.filter(Metric.time <= until)

    metrics = q.order_by(Metric.time.desc()).limit(limit).all()

    return [
        {
            "timestamp": m.time.isoformat(),
            "temp_C": float(m.temp_c) if m.temp_c is not None else None,
            "humedad_pct": float(m.humidity_pct) if m.humidity_pct is not None else None,
            "energia_kW": float(m.energy_kw) if m.energy_kw is not None else None,
        }
        for m in metrics
    ]
