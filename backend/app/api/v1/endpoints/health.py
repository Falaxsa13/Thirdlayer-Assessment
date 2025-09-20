from fastapi import APIRouter
from datetime import datetime
from app.schemas.events import HealthResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify the API is running
    """
    return HealthResponse(
        status="healthy", app_name=settings.app_name, version=settings.app_version, timestamp=datetime.utcnow()
    )
