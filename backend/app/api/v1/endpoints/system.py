from fastapi import APIRouter
from app.schemas.system import SystemStatusResponse
from app.services.diagnostics import get_full_system_status

router = APIRouter()


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    summary="Subsystem Diagnostic & Readiness Report",
    description=(
        "Performs real-time diagnostic checks against database, AI local runtime, "
        "model artifacts, and execution sandbox. Accurately reports ready, unavailable, "
        "not_configured, or not_trained without exposing sensitive credentials."
    ),
)
async def get_system_status() -> SystemStatusResponse:
    """Detailed platform diagnostics inspecting configured resources with bounded timeouts."""
    return await get_full_system_status()
