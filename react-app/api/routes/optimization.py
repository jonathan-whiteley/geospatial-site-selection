"""Optimization API endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException

from services.data_service import get_data_service
from models.schemas import (
    OptimizationParams, OptimizationResult,
    OptimizationLookupResponse, ExpansionCandidate
)

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get("/results", response_model=List[OptimizationResult])
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lookup", response_model=OptimizationLookupResponse)
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

        return OptimizationLookupResponse(
            selected_candidates=[
                ExpansionCandidate(**c) for c in result['selected_candidates']
            ],
            snapped_params=OptimizationParams(**result['snapped_params']),
            total_sales=result['total_sales']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
