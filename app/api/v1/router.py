from fastapi import APIRouter
from app.api.v1.endpoints import buildings, thresholds, metrics, alerts

api_router = APIRouter()
api_router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
api_router.include_router(thresholds.router, prefix="/thresholds", tags=["thresholds"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
