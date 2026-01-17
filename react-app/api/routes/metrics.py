"""Metrics API endpoints."""
from fastapi import APIRouter, HTTPException

from services.data_service import get_data_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/network")
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
        # Return raw dict to avoid Pydantic validation issues with DB types
        return metrics if metrics else {}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
