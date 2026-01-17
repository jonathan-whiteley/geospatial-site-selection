"""Optimization API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.data_service import get_data_service

router = APIRouter(prefix="/optimization", tags=["optimization"])


class OptimizationParams(BaseModel):
    """Input parameters for optimization lookup."""
    max_stores: int = 50
    min_dist_new: float = 2.0
    min_dist_existing: float = 2.0


@router.get("/results")
async def get_optimization_results():
    """
    Get all pre-computed optimization results.

    These are pre-computed for a grid of parameters:
    - max_stores: [10, 50, 100]
    - min_distance_new: [1.0, 2.0, 3.0]
    - min_distance_existing: [1.0, 2.0, 3.0]

    Returns:
        List of all pre-computed optimization combinations
    """
    try:
        service = get_data_service()
        results = service.load_optimization_results()
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lookup")
async def lookup_optimization(params: OptimizationParams):
    """
    Lookup pre-computed optimization results for given parameters.

    Parameters are snapped to the nearest pre-computed values:
    - max_stores: snapped to [10, 50, 100]
    - min_dist_new: snapped to [1.0, 2.0, 3.0]
    - min_dist_existing: snapped to [1.0, 2.0, 3.0]

    This provides O(1) lookup instead of O(n^2) runtime optimization.

    Returns:
        Selected candidates, snapped parameters, and total predicted sales
    """
    try:
        service = get_data_service()
        result = service.lookup_optimization(
            max_stores=params.max_stores,
            min_dist_new=params.min_dist_new,
            min_dist_existing=params.min_dist_existing
        )
        # Return raw dict to avoid Pydantic validation issues with DB types
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
