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
    - within_convenience_isochrone: Boolean for partner proximity
    - min_distance_to_existing: Distance to nearest current store
    - quality_tier: 'top_25', 'top_50', 'top_75', 'bottom_25'

    Returns:
        List of expansion candidates matching filter criteria
    """
    try:
        service = get_data_service()
        data = service.load_expansion_data()
        candidates = data.get('candidates', [])

        # Apply filters
        if min_sales is not None:
            candidates = [c for c in candidates if c.get('predicted_annual_sales', 0) >= min_sales]

        if max_sales is not None:
            candidates = [c for c in candidates if c.get('predicted_annual_sales', 0) <= max_sales]

        if min_population is not None:
            candidates = [c for c in candidates if c.get('population', 0) >= min_population]

        if max_population is not None:
            candidates = [c for c in candidates if c.get('population', 0) <= max_population]

        if fulfillment_strategy is not None:
            candidates = [c for c in candidates if c.get('fulfillment_strategy') == fulfillment_strategy]

        if quality_tier is not None:
            candidates = [c for c in candidates if c.get('quality_tier') == quality_tier]

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
