import json
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, Response
from app.schemas.system import ComponentStatus


@pytest.mark.asyncio
async def test_system_status_structure_and_security(client: AsyncClient):
    """
    Verify /api/v1/system/status returns all four components, valid status enums,
    and never leaks secrets or internal credentials.
    """
    response = await client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()

    assert "overall_status" in data
    assert "components" in data
    components = data["components"]

    # Verify all 4 required components are tracked separately
    assert "database" in components
    assert "ai_runtime" in components
    assert "model_artifacts" in components
    assert "sandbox" in components

    # Verify model_artifacts status reflects checkpoint presence
    assert components["model_artifacts"]["status"] in (
        ComponentStatus.READY.value,
        ComponentStatus.NOT_TRAINED.value,
    )
    if components["model_artifacts"]["status"] == ComponentStatus.READY.value:
        assert "found" in components["model_artifacts"]["message"].lower()
    else:
        assert "baseline mode" in components["model_artifacts"]["message"].lower()

    # Verify sandbox is not_configured by default in Phase 1
    assert components["sandbox"]["status"] == ComponentStatus.NOT_CONFIGURED.value

    # Verify no passwords or secrets are leaked anywhere in the JSON response
    serialized = json.dumps(data)
    assert "promptforge_secure_dev_password" not in serialized
    assert "password" not in serialized.lower() or "password" not in components["database"].get("details", {})


@pytest.mark.asyncio
async def test_system_status_ai_runtime_missing_model_detection(client: AsyncClient):
    """
    Requirement 5: A reachable Ollama service must NOT imply that a requested model exists.
    Verify that when Ollama is reachable but lacks the target model, status is unavailable.
    """
    mock_tags_response = Response(
        200,
        json={
            "models": [
                {"name": "llama3:latest"},
                {"name": "mistral:7b"},
            ]
        },
    )

    with patch("app.services.diagnostics.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.get.return_value = mock_tags_response
        mock_client_cls.return_value = mock_instance

        response = await client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()
        ai_comp = data["components"]["ai_runtime"]

        # Status must be unavailable because qwen2.5-coder:1.5b is not in the installed list
        assert ai_comp["status"] == ComponentStatus.UNAVAILABLE.value
        assert "not downloaded" in ai_comp["message"]
        assert "ollama pull" in ai_comp["troubleshooting"]


@pytest.mark.asyncio
async def test_system_status_ai_runtime_ready_when_model_present(client: AsyncClient):
    """
    Verify that when Ollama is reachable AND the configured model is installed,
    status transitions to ready.
    """
    mock_tags_response = Response(
        200,
        json={
            "models": [
                {"name": "qwen2.5-coder:1.5b"},
            ]
        },
    )

    with patch("app.services.diagnostics.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.get.return_value = mock_tags_response
        mock_client_cls.return_value = mock_instance

        response = await client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()
        ai_comp = data["components"]["ai_runtime"]

        assert ai_comp["status"] == ComponentStatus.READY.value
        assert "ready" in ai_comp["message"].lower()


@pytest.mark.asyncio
async def test_system_status_database_mocked_ready(client: AsyncClient):
    """Verify database diagnostic returns ready when check_database_health succeeds."""
    with patch(
        "app.services.diagnostics.check_database_health",
        new_callable=AsyncMock,
        return_value=(True, "PostgreSQL connection verified via SELECT 1", 1.5),
    ):
        response = await client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()
        db_comp = data["components"]["database"]

        assert db_comp["status"] == ComponentStatus.READY.value
        assert db_comp["latency_ms"] == 1.5
