from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import csv, io

from app.api.deps import get_db
from app.db.models.metric import Metric
from app.db.models.floor import Floor
from app.db.models.building import Building
from app.db.models.threshold import Threshold
from app.db.models.alert import Alert
from app.db.models.enums import Variable, AlertLevel, AlertStatus

from app.db.schemas.metric import MetricIn, MetricInBatch
from app.services.gemini_service import gemini_service
from app.db.schemas.alert import AlertCreate

router = APIRouter()


# ============================================================
# Helpers de dominio
# ============================================================

DEFAULT_THRESHOLDS = {
    Variable.temperature: (18.0, 28.0),  # °C
    Variable.humidity:    (30.0, 70.0),  # % (mantener para energía, pero no se usará para temp/hum)
    Variable.energy:      (0.0, 10.0),   # kW (ajústalo)
}

def _get_or_create_building(db: Session, code: str = "A") -> Building:
    b = db.query(Building).filter_by(code=code).first()
    if not b:
        b = Building(code=code)
        db.add(b); db.commit(); db.refresh(b)
    return b

def _get_or_create_floor(db: Session, building: Building, number: int) -> Floor:
    f = db.query(Floor).filter(Floor.building_id == building.id, Floor.number == number).first()
    if not f:
        f = Floor(number=number, name=f"Piso {number}", building_id=building.id)
        db.add(f); db.commit(); db.refresh(f)
    return f

def _active_thresholds_map(db: Session, floor_id: int) -> dict[Variable, Tuple[float, float]]:
    ths = (
        db.query(Threshold)
        .filter(Threshold.floor_id == floor_id, Threshold.is_active == True)
        .all()
    )
    out: dict[Variable, Tuple[float, float]] = {}
    for t in ths:
        out[t.variable] = (float(t.lower), float(t.upper))
    # fallback por defecto si faltan
    for var, band in DEFAULT_THRESHOLDS.items():
        out.setdefault(var, band)
    return out

# ============================================================
# Evaluación de umbrales
# ============================================================

def _evaluate_temperature(temp: Optional[float]) -> Tuple[Optional[AlertLevel], str]:
    """
    Evalúa temperatura según umbrales:
    - Informativa: 26-27.9°C
    - Media: 28-29.4°C
    - Crítica: ≥29.5°C
    """
    if temp is None:
        return None, "Sin datos de temperatura"
    
    if temp < 26.0:
        return AlertLevel.info, "Temperatura normal"
    elif 26.0 <= temp <= 27.9:
        return AlertLevel.info, "Temperatura ligeramente elevada. Se recomienda verificar el sistema de ventilación."
    elif 28.0 <= temp <= 29.4:
        return AlertLevel.medium, f"Temperatura alta ({temp}°C). Se recomienda activar sistemas de enfriamiento y revisar el flujo de aire."
    else:  # temp >= 29.5
        return AlertLevel.critical, f"Temperatura crítica ({temp}°C). Se requiere acción inmediata: aumentar ventilación, revisar sistemas de climatización y considerar evacuación si persiste."

def _evaluate_humidity(humidity: Optional[float]) -> Tuple[Optional[AlertLevel], str]:
    """
    Evalúa humedad relativa según umbrales:
    - Informativa: <25% o >70%
    - Media: <22% o >75%
    - Crítica: <20% o >80%
    """
    if humidity is None:
        return None, "Sin datos de humedad"
    
    if 25.0 <= humidity <= 70.0:
        return AlertLevel.info, "Humedad relativa normal"
    elif (22.0 <= humidity < 25.0) or (70.0 < humidity <= 75.0):
        return AlertLevel.info, f"Humedad fuera del rango óptimo ({humidity}%). Se recomienda ajustar el sistema de humidificación/deshumidificación."
    elif (20.0 <= humidity < 22.0) or (75.0 < humidity <= 80.0):
        return AlertLevel.medium, f"Humedad en rango medio ({humidity}%). Se recomienda revisar y ajustar sistemas de control de humedad para evitar problemas de confort o daños."
    else:  # humidity < 20.0 or humidity > 80.0
        if humidity < 20.0:
            return AlertLevel.critical, f"Humedad muy baja ({humidity}%). Se requiere acción inmediata: aumentar humidificación para evitar problemas respiratorios y estática."
        else:  # humidity > 80.0
            return AlertLevel.critical, f"Humedad muy alta ({humidity}%). Se requiere acción inmediata: activar deshumidificación para prevenir moho, condensación y problemas estructurales."

def _level_for(value: Optional[float], lo: float, hi: float) -> Optional[AlertLevel]:
    """Función legacy para energía y otros valores que no tienen umbrales específicos"""
    if value is None:
        return None
    if lo <= value <= hi:
        return AlertLevel.info
    span = max(hi - lo, 1e-9)
    dist = (lo - value) if value < lo else (value - hi)
    ratio = dist / span
    return AlertLevel.critical if ratio >= 0.25 else AlertLevel.medium

def _generate_detailed_summary(
    temp: Optional[float],
    humidity: Optional[float],
    energy: Optional[float],
    temp_level: Optional[AlertLevel],
    humidity_level: Optional[AlertLevel],
    energy_level: Optional[AlertLevel]
) -> Dict[str, any]:
    """
    Genera un resumen detallado con recomendaciones para cada variable
    """
    summary = {
        "temperatura": {
            "valor": temp,
            "nivel": temp_level.value if temp_level else None,
            "recomendacion": None
        },
        "humedad": {
            "valor": humidity,
            "nivel": humidity_level.value if humidity_level else None,
            "recomendacion": None
        },
        "energia": {
            "valor": energy,
            "nivel": energy_level.value if energy_level else None,
            "recomendacion": None
        }
    }
    
    # Evaluar temperatura
    _, temp_rec = _evaluate_temperature(temp)
    summary["temperatura"]["recomendacion"] = temp_rec
    
    # Evaluar humedad
    _, hum_rec = _evaluate_humidity(humidity)
    summary["humedad"]["recomendacion"] = hum_rec
    
    # Evaluar energía (usar lógica legacy)
    if energy is not None:
        if energy_level == AlertLevel.critical:
            summary["energia"]["recomendacion"] = f"Consumo de energía crítico ({energy} kW). Revisar equipos y optimizar uso."
        elif energy_level == AlertLevel.medium:
            summary["energia"]["recomendacion"] = f"Consumo de energía elevado ({energy} kW). Monitorear tendencias."
        else:
            summary["energia"]["recomendacion"] = "Consumo de energía normal"
    else:
        summary["energia"]["recomendacion"] = "Sin datos de energía"
    
    return summary

def _brief_summary(values: dict, levels: dict[Variable, Optional[AlertLevel]]) -> str:
    """Resumen breve para compatibilidad"""
    msgs = []
    if levels.get(Variable.temperature) in (AlertLevel.medium, AlertLevel.critical):
        msgs.append(f"Temp {values.get('temp_C')}°C")
    if levels.get(Variable.humidity) in (AlertLevel.medium, AlertLevel.critical):
        msgs.append(f"Humedad {values.get('humedad_pct')}%")
    if levels.get(Variable.energy) in (AlertLevel.medium, AlertLevel.critical):
        msgs.append(f"Energía {values.get('energia_kW')} kW")
    return ", ".join(msgs) if msgs else "Dentro de rangos"


# ============================================================
# Ingesta JSON
# ============================================================

@router.post("/ingest", status_code=201)
def ingest_metrics_json(payload: MetricIn | MetricInBatch, db: Session = Depends(get_db)):
    items: List[MetricIn] = payload.items if isinstance(payload, MetricInBatch) else [payload]
    if not items:
        raise HTTPException(status_code=400, detail="No hay registros para ingresar")

    to_insert: list[Metric] = []
    alerts_created = []
    
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
        
        # Detectar anomalías y crear alertas
        try:
            _detect_and_create_alerts(
                db,
                floor,
                float(it.temp_C) if it.temp_C else None,
                float(it.humedad_pct) if it.humedad_pct else None,
                float(it.energia_kW) if it.energia_kW else None
            )
        except Exception as e:
            print(f"Error detectando anomalías: {e}")

    db.bulk_save_objects(to_insert)
    db.commit()

    return {
        "ingested": len(to_insert),
        "first_ts": str(min(i.timestamp for i in items)),
        "last_ts": str(max(i.timestamp for i in items)),
        "buildings": sorted({i.edificio for i in items}),
    }


# ============================================================
# Ingesta CSV
# ============================================================

@router.post("/upload-csv", status_code=201)
async def upload_metrics_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=400, detail=f"Encabezado esperado: {','.join(sorted(expected))}")

    rows: list[Metric] = []
    count = 0
    min_ts: datetime | None = None
    max_ts: datetime | None = None

    for r in reader:
        ts_raw = r["timestamp"].strip().replace("Z", "+00:00")
        try:
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

    return {"ingested": count, "first_ts": str(min_ts), "last_ts": str(max_ts)}


# ============================================================
# LISTA mejorada (filtros + paginación simple)
# ============================================================

@router.get("/", summary="Listar métricas", response_model=list[dict])
def list_metrics(
    edificio: str,
    piso: int,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    building = db.query(Building).filter_by(code=edificio).first()
    if not building:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")

    floor = db.query(Floor).filter(Floor.building_id == building.id, Floor.number == piso).first()
    if not floor:
        raise HTTPException(status_code=404, detail="Piso no encontrado")

    q = db.query(Metric).filter(Metric.floor_id == floor.id)
    if since: q = q.filter(Metric.time >= since)
    if until: q = q.filter(Metric.time <= until)

    total = q.count()
    rows = q.order_by(Metric.time.desc()).offset(offset).limit(limit).all()

    payload = [
        {
            "timestamp": m.time.isoformat(),
            "temp_C": float(m.temp_c) if m.temp_c is not None else None,
            "humedad_pct": float(m.humidity_pct) if m.humidity_pct is not None else None,
            "energia_kW": float(m.energy_kw) if m.energy_kw is not None else None,
        }
        for m in rows
    ]
    return [{"total": total, "count": len(payload), "data": payload}]


# ============================================================
# TENDENCIAS (últimas N horas)
# ============================================================

@router.get("/trends", summary="Series de tiempo para gráficas", response_model=dict)
def trends(
    edificio: str,
    piso: int,
    hours: int = Query(4, ge=1, le=24),
    db: Session = Depends(get_db),
):
    building = db.query(Building).filter_by(code=edificio).first()
    if not building:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")
    floor = db.query(Floor).filter(Floor.building_id == building.id, Floor.number == piso).first()
    if not floor:
        raise HTTPException(status_code=404, detail="Piso no encontrado")

    since = datetime.utcnow() - timedelta(hours=hours)
    qs = (
        db.query(Metric)
        .filter(Metric.floor_id == floor.id, Metric.time >= since)
        .order_by(Metric.time.asc())
        .all()
    )
    return {
        "timestamps": [m.time.isoformat() for m in qs],
        "temp_C": [float(m.temp_c) if m.temp_c is not None else None for m in qs],
        "humedad_pct": [float(m.humidity_pct) if m.humidity_pct is not None else None for m in qs],
        "energia_kW": [float(m.energy_kw) if m.energy_kw is not None else None for m in qs],
    }


# ============================================================
# TARJETAS por piso (estado + resumen MEJORADO)
# ============================================================

@router.get("/cards", summary="Tarjetas por piso (estado y resumen con recomendaciones)", response_model=list[dict])
def floor_cards(
    edificio: str,
    db: Session = Depends(get_db),
):
    building = db.query(Building).filter_by(code=edificio).first()
    if not building:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")

    result = []
    for floor in db.query(Floor).filter(Floor.building_id == building.id).order_by(Floor.number.asc()):
        # último registro del piso
        last: Metric | None = (
            db.query(Metric)
            .filter(Metric.floor_id == floor.id)
            .order_by(Metric.time.desc())
            .first()
        )
        if not last:
            result.append({
                "piso": floor.number,
                "estado": "sin datos",
                "resumen": "—",
                "detalle": {
                    "temperatura": {"valor": None, "nivel": None, "recomendacion": "Sin datos"},
                    "humedad": {"valor": None, "nivel": None, "recomendacion": "Sin datos"},
                    "energia": {"valor": None, "nivel": None, "recomendacion": "Sin datos"}
                }
            })
            continue

        # Obtener valores
        temp = float(last.temp_c) if last.temp_c is not None else None
        humidity = float(last.humidity_pct) if last.humidity_pct is not None else None
        energy = float(last.energy_kw) if last.energy_kw is not None else None

        # Evaluar usando los umbrales específicos de la imagen
        temp_level, temp_rec = _evaluate_temperature(temp)
        humidity_level, hum_rec = _evaluate_humidity(humidity)
        
        # Para energía, usar umbrales legacy si existen
        th = _active_thresholds_map(db, floor.id)
        energy_level = _level_for(energy, *th.get(Variable.energy, (0.0, 10.0)))

        # Generar resumen detallado
        detalle = _generate_detailed_summary(
            temp, humidity, energy,
            temp_level, humidity_level, energy_level
        )

        # Estado general = peor de los niveles presentes
        order = {None: 0, AlertLevel.info: 1, AlertLevel.medium: 2, AlertLevel.critical: 3}
        worst = max(
            [temp_level, humidity_level, energy_level],
            key=lambda x: order.get(x, 0)
        )
        estado = {
            None: "OK",
            AlertLevel.info: "OK",
            AlertLevel.medium: "Media",
            AlertLevel.critical: "Crítica"
        }[worst]

        # Resumen breve (para compatibilidad)
        vals = {
            "temp_C": temp,
            "humedad_pct": humidity,
            "energia_kW": energy,
        }
        levels = {
            Variable.temperature: temp_level,
            Variable.humidity: humidity_level,
            Variable.energy: energy_level,
        }
        resumen = _brief_summary(vals, levels)

        result.append({
            "piso": floor.number,
            "estado": estado,
            "resumen": resumen,
            "timestamp": last.time.isoformat(),
            "valores": vals,
            "detalle": detalle,
        })

    return result


# ============================================================
# TABLA de alertas (filtros por piso/nivel)
# ============================================================

@router.get("/alerts", summary="Tabla de alertas", response_model=list[dict])
def alerts_table(
    edificio: str,
    piso: Optional[int] = None,
    nivel: Optional[AlertLevel] = Query(None, description="info | medium | critical"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
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

    rows = q.order_by(Alert.created_at.desc()).limit(limit).all()

    out = []
    for alert, piso_num in rows:
        out.append({
            "timestamp": alert.created_at.isoformat(),
            "piso": piso_num,
            "variable": alert.variable.value,
            "nivel": alert.level.value,
            "recomendacion": alert.recommendation,
            "mensaje": alert.message,
        })
    return out


# ============================================================
# Detección automática de anomalías y generación de alertas
# ============================================================

def _should_create_alert(
    db: Session,
    floor_id: int,
    variable: Variable,
    level: AlertLevel
) -> bool:
    """
    Verifica si se debe crear una nueva alerta (evita duplicados recientes)
    """
    if level == AlertLevel.info:
        return False  # No crear alertas informativas automáticamente
    
    # Buscar alertas similares abiertas en los últimos 30 minutos
    recent = (
        db.query(Alert)
        .filter(
            Alert.floor_id == floor_id,
            Alert.variable == variable,
            Alert.status == AlertStatus.open,
            Alert.created_at >= datetime.utcnow() - timedelta(minutes=30)
        )
        .first()
    )
    return recent is None

def _create_alert_from_anomaly(
    db: Session,
    floor: Floor,
    variable: Variable,
    level: AlertLevel,
    value: float,
    message: str
) -> Optional[Alert]:
    """
    Crea una alerta con recomendación generada por Gemini AI
    """
    if not _should_create_alert(db, floor.id, variable, level):
        return None
    
    # Obtener contexto histórico reciente (últimas 2 horas)
    historical = (
        db.query(Metric)
        .filter(
            Metric.floor_id == floor.id,
            Metric.time >= datetime.utcnow() - timedelta(hours=2)
        )
        .order_by(Metric.time.desc())
        .limit(10)
        .all()
    )
    
    historical_context = {
        "count": len(historical),
        "trend": "increasing" if len(historical) > 1 and historical[0].temp_c and historical[-1].temp_c and historical[0].temp_c > historical[-1].temp_c else "stable"
    }
    
    # Generar recomendación con Gemini
    recommendation = gemini_service.generate_recommendation(
        variable=variable,
        level=level,
        floor_number=floor.number,
        current_value=value,
        historical_context=historical_context
    )
    
    alert = Alert(
        floor_id=floor.id,
        variable=variable,
        level=level,
        status=AlertStatus.open,
        message=message,
        recommendation=recommendation
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

def _detect_and_create_alerts(
    db: Session,
    floor: Floor,
    temp: Optional[float],
    humidity: Optional[float],
    energy: Optional[float]
):
    """
    Detecta anomalías y crea alertas automáticamente
    """
    # Evaluar temperatura
    if temp is not None:
        temp_level, temp_msg = _evaluate_temperature(temp)
        if temp_level in (AlertLevel.medium, AlertLevel.critical):
            _create_alert_from_anomaly(
                db, floor, Variable.temperature, temp_level, temp, temp_msg
            )
    
    # Evaluar humedad
    if humidity is not None:
        hum_level, hum_msg = _evaluate_humidity(humidity)
        if hum_level in (AlertLevel.medium, AlertLevel.critical):
            _create_alert_from_anomaly(
                db, floor, Variable.humidity, hum_level, humidity, hum_msg
            )
    
    # Evaluar energía (usar umbrales legacy)
    if energy is not None:
        th = _active_thresholds_map(db, floor.id)
        energy_level = _level_for(energy, *th.get(Variable.energy, (0.0, 10.0)))
        if energy_level in (AlertLevel.medium, AlertLevel.critical):
            energy_msg = f"Consumo de energía fuera de rango: {energy} kW"
            _create_alert_from_anomaly(
                db, floor, Variable.energy, energy_level, energy, energy_msg
            )
