"""Metrics API endpoints."""
from fastapi import APIRouter, HTTPException

from services.data_service import get_data_service
from models.schemas import NetworkMetrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/network", response_model=NetworkMetrics)
async def get_network_metrics():
    """
    Get pre-computed network-wide metrics.

    Returns:
        Aggregate metrics including store counts, sales totals,
        and partnership opportunity rates
    """
    try:
        service = get_data_service()
        metrics = service.load_network_metrics()
        return NetworkMetrics(**metrics) if metrics else NetworkMetrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
