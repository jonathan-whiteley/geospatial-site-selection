"""Store-related API endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException

from services.data_service import get_data_service
from models.schemas import (
    Store, Isochrone, ConvenienceIsochrone,
    ConvenienceStore, Competitor, CurrentNetworkResponse
)

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/current", response_model=List[Store])
async def get_current_stores():
    """
    Get all current store locations.

    Returns:
        List of current stores with location and sales data
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return data.get('stores', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/isochrones", response_model=List[Isochrone])
async def get_store_isochrones():
    """
    Get LCE store trade area isochrones (drive time polygons).

    Returns:
        List of isochrone GeoJSON polygons for MA stores
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return data.get('isochrones', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convenience", response_model=List[ConvenienceIsochrone])
async def get_convenience_isochrones():
    """
    Get convenience store trade area isochrones with candidate info.

    Returns:
        List of convenience isochrones with overlapping candidate counts
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return data.get('convenience_isochrones', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/convenience/stores", response_model=List[ConvenienceStore])
async def get_convenience_stores():
    """
    Get potential partner convenience store locations.

    Returns:
        List of convenience stores that could serve as partners
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return data.get('convenience_stores', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/competitors", response_model=List[Competitor])
async def get_competitors():
    """
    Get competitor store locations.

    Returns:
        List of competitor locations
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return data.get('competitors', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network", response_model=CurrentNetworkResponse)
async def get_full_network():
    """
    Get all current network data in a single request.

    Returns:
        Complete network data including stores, isochrones, convenience, competitors
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return CurrentNetworkResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
