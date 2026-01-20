"""Expansion analysis API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from services.data_service import get_data_service
from models.schemas import ExpansionCandidate, ExpansionDataResponse

router = APIRouter(prefix="/expansion", tags=["expansion"])


@router.get("/candidates", response_model=List[ExpansionCandidate])
async def get_expansion_candidates(
    min_sales: Optional[float] = Query(None, description="Minimum predicted annual sales"),
    max_sales: Optional[float] = Query(None, description="Maximum predicted annual sales"),
    min_population: Optional[float] = Query(None, description="Minimum population"),
    max_population: Optional[float] = Query(None, description="Maximum population"),
    fulfillment_strategy: Optional[str] = Query(None, description="Filter by strategy: partner or new_store"),
    quality_tier: Optional[str] = Query(None, description="Filter by quality tier: top_25, top_50, etc.")
):
    """
    Get expansion candidate locations with optional filtering.

    Pre-computed fields include:
    - fulfillment_strategy: 'partner' or 'new_store'
    - within_partner_isochrone: Boolean for partner proximity
    - min_distance_to_existing: Distance to nearest current store
    - quality_tier: 'top_25', 'top_50', 'top_75', 'bottom_25'

    Returns:
        List of expansion candidates matching filter criteria
    """
    try:
        service = get_data_service()
        # Phase 2.4: Push filters to SQL for better performance
        candidates = service.load_expansion_candidates(
            min_sales=min_sales,
            max_sales=max_sales,
            min_population=min_population,
            max_population=max_population,
            fulfillment_strategy=fulfillment_strategy,
            quality_tier=quality_tier
        )
        return candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data")
async def get_expansion_data():
    """
    Get all expansion analysis data in a single request.

    Returns:
        Complete expansion data including candidates, current stores,
        convenience stores, and competitors
    """
    try:
        service = get_data_service()
        data = service.load_expansion_data()
        # Return raw dict to avoid Pydantic validation issues with DB types
        return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
