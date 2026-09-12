from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.core.config import settings

api_v1_router = APIRouter()


@api_v1_router.get("/ping", response_model=HealthResponse, tags=["System"])
async def ping() -> HealthResponse:
    """Ping endpoint under v1 namespace."""
    return HealthResponse(
        status="ok",
        app_env=settings.APP_ENV,
        version="0.1.0"
    )
