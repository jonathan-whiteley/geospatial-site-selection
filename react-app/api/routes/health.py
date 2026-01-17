"""Health check endpoint."""
from fastapi import APIRouter, HTTPException

from core.config import get_settings
from core.database import get_db
from models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check API health and database connectivity.

    Returns:
        Health status including auth type and database status
    """
    settings = get_settings()
    db = get_db()

    # Determine auth type
    auth_type = "service_principal" if settings.is_service_principal else "pat_token"

    # Test database connection
    try:
        df = db.execute_query("SELECT 1 as test")
        db_status = "connected" if not df.empty else "no_data"
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

    return HealthResponse(
        status="healthy",
        database=db_status,
        auth_type=auth_type
    )
