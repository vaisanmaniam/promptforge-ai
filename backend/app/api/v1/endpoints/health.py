from fastapi import APIRouter
from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application Liveness Probe",
    description="Returns immediate application liveness status decoupled from downstream dependencies.",
)
async def get_health() -> HealthResponse:
    """Liveness probe: verifies that the FastAPI application is alive and accepting traffic."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )
