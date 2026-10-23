"""
API Integration tests for /api/v1/requirements endpoints.
Verifies requirement extraction, specification persistence, graph querying,
impact analysis, coverage, and validation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_extract_requirements_endpoint_success():
    """Verify POST /api/v1/requirements/extract returns valid specification, validation, and coverage."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/requirements/extract",
            json={
                "prompt": "Build a secure user authentication service in FastAPI with bcrypt password hashing and JWT access tokens.",
                "task_category": "api_development",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "specification" in data
        assert "validation" in data
        assert "coverage" in data

        spec = data["specification"]
        assert len(spec["requirements"]) >= 3
        assert spec["task_category"] == "api_development"
        assert "category_breakdown" in spec

        # Verify acceptance criteria are present
        for req in spec["requirements"]:
            assert len(req["acceptance_criteria"]) > 0


@pytest.mark.asyncio
async def test_specifications_crud_and_graph_flow():
    """Verify specification creation, listing, retrieval, graph, impact, and coverage."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create Specification
        create_resp = await client.post(
            "/api/v1/requirements/specifications",
            json={
                "title": "CRUD Test Specification",
                "prompt": "Create an LRU cache in Python with thread-safe locks and O(1) eviction.",
            },
        )
        assert create_resp.status_code == 201
        spec = create_resp.json()
        spec_id = spec["id"]
        assert spec_id.startswith("spec-")

        # 2. List Specifications
        list_resp = await client.get("/api/v1/requirements/specifications")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert any(s["id"] == spec_id for s in list_data["specifications"])

        # 3. Get Specification by ID
        get_resp = await client.get(f"/api/v1/requirements/specifications/{spec_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == spec_id

        # 4. Get Traceability Graph
        graph_resp = await client.get(f"/api/v1/requirements/specifications/{spec_id}/graph")
        assert graph_resp.status_code == 200
        graph_data = graph_resp.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert any(n["id"] == "PROMPT-ROOT" for n in graph_data["nodes"])

        # 5. Get Impact Analysis for first requirement
        req1_id = spec["requirements"][0]["id"]
        impact_resp = await client.get(f"/api/v1/requirements/specifications/{spec_id}/impact/{req1_id}")
        assert impact_resp.status_code == 200
        impact_data = impact_resp.json()
        assert impact_data["target_req_id"] == req1_id
        assert "risk_level" in impact_data

        # 6. Get Coverage Report
        cov_resp = await client.get(f"/api/v1/requirements/specifications/{spec_id}/coverage")
        assert cov_resp.status_code == 200
        cov_data = cov_resp.json()
        assert cov_data["prompt_coverage_pct"] == 100.0
        assert cov_data["code_traceability_status"] == "pending_phase_4"

        # 7. Get Validation Report
        val_resp = await client.get(f"/api/v1/requirements/specifications/{spec_id}/validation")
        assert val_resp.status_code == 200
        val_data = val_resp.json()
        assert "findings" in val_data


@pytest.mark.asyncio
async def test_get_nonexistent_specification_returns_404():
    """Verify 404 response for unknown specification ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/requirements/specifications/spec-nonexistent-123")
        assert response.status_code == 404
