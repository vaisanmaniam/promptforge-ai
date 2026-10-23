"""
Integration tests for Predictive Regression Testing API endpoints.
Validates /analyze, /prioritize, /select, /model/status, /history, and /model/train.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_regression_api_full_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest calculator project first
        preset_resp = await ac.post(
            "/api/v1/verification/projects/json",
            json={
                "name": "Calculator Service",
                "files": {
                    "calculator.py": "def add(a, b):\n    return a + b\n",
                    "tests/test_calculator.py": "from calculator import add\ndef test_add():\n    assert add(1, 2) == 3\n",
                },
            },
        )
        assert preset_resp.status_code == 201
        project_data = preset_resp.json()
        project_id = project_data["project_id"]

        # 2. Test /regression/model/status
        status_resp = await ac.get("/api/v1/regression/model/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "status" in status_data
        assert "model_name" in status_data

        # 3. Test /regression/analyze
        analyze_resp = await ac.post(
            "/api/v1/regression/analyze",
            json={
                "project_id": project_id,
                "changed_files": ["calculator.py"],
            },
        )
        assert analyze_resp.status_code == 200
        analyze_data = analyze_resp.json()
        assert analyze_data["project_id"] == project_id
        assert len(analyze_data["changed_files"]) == 1
        analysis_id = analyze_data["analysis_id"]

        # 4. Test /regression/analyses/{id}
        get_anl_resp = await ac.get(f"/api/v1/regression/analyses/{analysis_id}")
        assert get_anl_resp.status_code == 200

        # 5. Test /regression/prioritize
        prioritize_resp = await ac.post(
            "/api/v1/regression/prioritize",
            json={
                "project_id": project_id,
                "changed_files": ["calculator.py"],
                "strategy": "predictive",
            },
        )
        assert prioritize_resp.status_code == 200
        p_data = prioritize_resp.json()
        assert len(p_data["ranked_tests"]) >= 1
        assert isinstance(p_data["fallback_to_baseline"], bool)

        # 6. Test /regression/select
        select_resp = await ac.post(
            "/api/v1/regression/select",
            json={
                "project_id": project_id,
                "changed_files": ["calculator.py"],
                "strategy": "predictive",
                "top_k": 1,
            },
        )
        assert select_resp.status_code == 200
        sel_data = select_resp.json()
        assert sel_data["selected_count"] == 1
        assert len(sel_data["selected_tests"]) == 1

        # 7. Test /regression/history
        hist_resp = await ac.get("/api/v1/regression/history")
        assert hist_resp.status_code == 200
        assert isinstance(hist_resp.json(), list)

        # 8. Test /regression/model/train with synthetic test data
        train_resp = await ac.post(
            "/api/v1/regression/model/train",
            json={
                "include_synthetic": True,
                "algorithm": "RandomForestClassifier",
            },
        )
        assert train_resp.status_code == 200
        train_data = train_resp.json()
        assert train_data["success"] is True
        assert train_data["status"] == "trained"
