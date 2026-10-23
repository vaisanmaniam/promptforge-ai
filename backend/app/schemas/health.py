from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response model."""
    status: str = Field(default="healthy", description="Application liveness status")
    version: str = Field(description="PromptForge AI version")
    environment: str = Field(description="Current deployment environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp of check"
    )
