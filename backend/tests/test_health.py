import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Verify application liveness probe is independent, fast, and healthy."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Verify root discovery endpoint returns documentation and status paths."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "PromptForge AI"
    assert data["health"] == "/api/v1/health"
    assert data["system_status"] == "/api/v1/system/status"
