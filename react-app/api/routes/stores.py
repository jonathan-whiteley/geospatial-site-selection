"""Store-related API endpoints."""
from fastapi import APIRouter, HTTPException

from services.data_service import get_data_service

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/current")
async def get_current_stores():
    """
    Get all current store locations.

    Returns:
        List of current stores with location and sales data
    """
    try:
        service = get_data_service()
        # Use individual loader for better performance
        return service.load_stores()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/isochrones")
async def get_store_isochrones():
    """
    Get LCE store trade area isochrones (drive time polygons).

    Returns:
        List of isochrone GeoJSON polygons for MA stores
    """
    try:
        service = get_data_service()
        # Use individual loader for better performance
        return service.load_isochrones()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/partners")
async def get_partner_isochrones():
    """
    Get partner store trade area isochrones with candidate info.

    Returns:
        List of partner isochrones with overlapping candidate counts
    """
    try:
        service = get_data_service()
        partner_data = service.load_partner_data()
        return partner_data['isochrones']
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/partners/stores")
async def get_partner_stores():
    """
    Get potential partner store locations (e.g., convenience stores).

    Returns:
        List of partner stores that could serve as fulfillment locations
    """
    try:
        service = get_data_service()
        partner_data = service.load_partner_data()
        return partner_data['stores']
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Backward compatibility aliases (deprecated)
@router.get("/convenience")
async def get_convenience_isochrones():
    """
    DEPRECATED: Use /stores/partners instead.
    Get partner store trade area isochrones with candidate info.
    """
    return await get_partner_isochrones()


@router.get("/convenience/stores")
async def get_convenience_stores():
    """
    DEPRECATED: Use /stores/partners/stores instead.
    Get potential partner store locations.
    """
    return await get_partner_stores()


@router.get("/competitors")
async def get_competitors():
    """
    Get competitor store locations.

    Returns:
        List of competitor locations
    """
    try:
        service = get_data_service()
        # Use individual loader for better performance
        return service.load_competitors()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers")
async def get_customer_locations():
    """
    Get customer device locations.

    Returns:
        List of customer locations with device ID and home store
    """
    try:
        service = get_data_service()
        return service.load_customers()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network")
async def get_full_network():
    """
    Get all current network data in a single request.

    Returns:
        Complete network data including stores, isochrones, partners, competitors
    """
    try:
        service = get_data_service()
        data = service.load_current_network_data()
        return data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
