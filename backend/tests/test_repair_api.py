"""
Integration tests for Failure-Guided Automated Code Repair REST API endpoints.
Tests full workflow: project ingestion -> failure analysis -> proposal generation ->
approval -> patch application -> rollback -> audit history and runtime status.
"""

from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app
from app.schemas.verification import ExecutionStatus, VerificationRun
from app.services.verification.storage import VerificationRepository


@pytest.mark.asyncio
async def test_repair_api_full_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest project with buggy function
        ingest_resp = await ac.post(
            "/api/v1/verification/projects/json",
            json={
                "name": "Math Bug Project",
                "files": {
                    "calc.py": "def subtract(a, b):\n    return a + b\n",
                    "tests/test_calc.py": "from calc import subtract\ndef test_subtract():\n    assert subtract(5, 3) == 2\n",
                },
            },
        )
        assert ingest_resp.status_code == 201
        proj = ingest_resp.json()
        project_id = proj["project_id"]

        # 2. Simulate a verification run with a pytest failure
        v_repo = VerificationRepository()
        failure_stdout = """
=================================== FAILURES ===================================
________________________________ test_subtract _________________________________
    def test_subtract():
>       assert subtract(5, 3) == 2
E       assert 8 == 2
E        +  where 8 = subtract(5, 3)
tests/test_calc.py:3: AssertionError
=========================== short test summary info ============================
FAILED tests/test_calc.py::test_subtract - assert 8 == 2
============================== 1 failed in 0.05s ===============================
"""
        sim_run = VerificationRun(
            id=f"run-sim-{project_id[:6]}",
            project_id=project_id,
            status=ExecutionStatus.FAILED,
            total_tests=1,
            passed_tests=0,
            failed_tests=1,
            stdout=failure_stdout,
            stderr="",
            duration_ms=45.0,
            created_at="",
        )
        await v_repo.save_run(sim_run)

        # 3. Test runtime status endpoint
        rt_resp = await ac.get("/api/v1/repair/runtime/status")
        assert rt_resp.status_code == 200
        rt_data = rt_resp.json()
        assert rt_data["deterministic_engine"] is True
        assert "local_code_model" in rt_data
        assert "docker_sandbox" in rt_data

        # 4. Trigger failure analysis
        analyze_resp = await ac.post(f"/api/v1/repair/analyze/{sim_run.id}")
        assert analyze_resp.status_code == 200
        failures = analyze_resp.json()
        assert len(failures) >= 1
        fail_rep = failures[0]
        failure_id = fail_rep["failure_id"]
        assert fail_rep["category"] == "assertion_failure"
        assert fail_rep["classification"] == "code_defect"
        assert len(fail_rep["hypotheses"]) >= 1

        # 5. Get individual failure report
        get_fail_resp = await ac.get(f"/api/v1/repair/failures/{failure_id}")
        assert get_fail_resp.status_code == 200
        assert get_fail_resp.json()["failure_id"] == failure_id

        # 6. Generate repair proposal
        prop_resp = await ac.post(
            "/api/v1/repair/proposals",
            json={"failure_id": failure_id},
        )
        assert prop_resp.status_code == 201
        proposal = prop_resp.json()
        repair_id = proposal["repair_id"]
        assert proposal["status"] == "proposed"
        assert "return a - b" in proposal["patched_content"]
        assert proposal["generator_type"] == "deterministic_rule_engine"
        assert "@@" in proposal["unified_diff"]

        # 7. List proposals
        list_resp = await ac.get(f"/api/v1/repair/proposals?project_id={project_id}")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 8. Get proposal by ID
        get_prop_resp = await ac.get(f"/api/v1/repair/proposals/{repair_id}")
        assert get_prop_resp.status_code == 200
        assert get_prop_resp.json()["repair_id"] == repair_id

        # 9. Try applying without approval -> must fail 400
        apply_early = await ac.post(f"/api/v1/repair/proposals/{repair_id}/apply")
        assert apply_early.status_code == 400

        # 10. Approve proposal
        approve_resp = await ac.post(
            f"/api/v1/repair/proposals/{repair_id}/approve",
            json={"decision_reason": "Verified fix fixes addition operator"},
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # 11. Apply proposal to workspace
        apply_resp = await ac.post(f"/api/v1/repair/proposals/{repair_id}/apply")
        assert apply_resp.status_code == 200
        app_data = apply_resp.json()
        assert app_data["success"] is True
        assert app_data["rollback_available"] is True

        # Check proposal status is now APPLIED
        get_applied = await ac.get(f"/api/v1/repair/proposals/{repair_id}")
        assert get_applied.json()["status"] == "applied"

        # 12. Rollback proposal
        rb_resp = await ac.post(f"/api/v1/repair/proposals/{repair_id}/rollback")
        assert rb_resp.status_code == 200
        assert rb_resp.json()["success"] is True
        assert rb_resp.json()["status"] == "rolled_back"

        # 13. Audit history
        hist_resp = await ac.get(f"/api/v1/repair/history?repair_id={repair_id}")
        assert hist_resp.status_code == 200
        history = hist_resp.json()
        actions = [h["action"] for h in history]
        assert "PROPOSE" in actions
        assert "APPROVE" in actions
        assert "APPLY" in actions
        assert "ROLLBACK" in actions
