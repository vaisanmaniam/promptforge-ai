from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ComponentStatus(str, Enum):
    """Component availability status states."""
    READY = "ready"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"
    NOT_TRAINED = "not_trained"


class ComponentDiagnostic(BaseModel):
    """Individual subsystem diagnostic evaluation."""
    status: ComponentStatus = Field(description="Component operational status")
    message: str = Field(description="Human-readable status summary")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Diagnostic details without secrets")
    troubleshooting: Optional[str] = Field(default=None, description="Actionable command or configuration guide")
    latency_ms: Optional[float] = Field(default=None, description="Check duration in milliseconds")


class SystemStatusResponse(BaseModel):
    """Aggregated platform diagnostic response."""
    overall_status: str = Field(description="'ready', 'degraded', or 'setup_required'")
    version: str = Field(description="Platform release version")
    environment: str = Field(description="Operating environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp of inspection"
    )
    components: Dict[str, ComponentDiagnostic] = Field(
        description="Map of component diagnostics: database, ai_runtime, model_artifacts, sandbox"
    )
