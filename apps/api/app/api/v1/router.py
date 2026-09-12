from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.core.config import settings
from app.api.v1.projects import router as projects_router
from app.api.v1.assets import router as assets_router

api_v1_router = APIRouter()

# System ping endpoint
@api_v1_router.get("/ping", response_model=HealthResponse, tags=["System"])
async def ping() -> HealthResponse:
    """Ping endpoint under v1 namespace."""
    return HealthResponse(
        status="ok",
        app_env=settings.APP_ENV,
        version="0.1.0"
    )

# Include projects and assets routes
api_v1_router.include_router(projects_router)
api_v1_router.include_router(assets_router)
