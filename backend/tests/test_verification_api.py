"""
API Integration tests for /api/v1/verification and /api/v1/requirements/.../evidence endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_verification_api_full_flow():
    """Verify project ingestion, requirement linking, run triggering, and evidence endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Check Docker status endpoint
        doc_resp = await client.get("/api/v1/verification/docker-status")
        assert doc_resp.status_code == 200
        doc_data = doc_resp.json()
        assert "docker_available" in doc_data
        assert "fail_closed_policy" in doc_data

        # 2. Ingest project via JSON payload
        project_payload = {
            "name": "LRU Cache Service",
            "files": {
                "src/lru_cache.py": (
                    "class LRUCache:\n"
                    "    # Implements REQ-001\n"
                    "    def __init__(self, capacity: int):\n"
                    "        self.capacity = capacity\n"
                    "        self.cache = {}\n"
                    "    def get(self, key):\n"
                    "        return self.cache.get(key)\n"
                    "    def put(self, key, value):\n"
                    "        self.cache[key] = value\n"
                ),
                "tests/test_lru_cache.py": (
                    "from src.lru_cache import LRUCache\n"
                    "def test_req_001_cache_operations():\n"
                    "    c = LRUCache(2)\n"
                    "    c.put('a', 1)\n"
                    "    assert c.get('a') == 1\n"
                ),
                "requirements.txt": "pytest>=8.0.0\n",
            },
        }

        ingest_resp = await client.post("/api/v1/verification/projects/json", json=project_payload)
        assert ingest_resp.status_code == 201
        project = ingest_resp.json()
        project_id = project["project_id"]
        assert project_id.startswith("prj-")
        assert project["total_files"] == 3

        # 3. Retrieve project artifacts
        art_resp = await client.get(f"/api/v1/verification/projects/{project_id}/artifacts")
        assert art_resp.status_code == 200
        artifacts = art_resp.json()
        assert len(artifacts) == 3
        assert any(a["relative_path"] == "src/lru_cache.py" for a in artifacts)

        # 4. Create a specification to link against
        spec_resp = await client.post(
            "/api/v1/requirements/specifications",
            json={
                "title": "LRU Cache Spec",
                "prompt": "Implement an LRU cache in Python with O(1) eviction and capacity limit.",
            },
        )
        assert spec_resp.status_code == 201
        spec = spec_resp.json()
        spec_id = spec["id"]

        # 5. Link requirements
        link_resp = await client.post(
            f"/api/v1/verification/projects/{project_id}/link-requirements",
            json={"specification_id": spec_id},
        )
        assert link_resp.status_code == 200
        links = link_resp.json()
        assert len(links) >= 1

        # 6. Retrieve links
        get_links_resp = await client.get(f"/api/v1/verification/projects/{project_id}/traceability")
        assert get_links_resp.status_code == 200
        assert len(get_links_resp.json()) == len(links)

        # 7. Confirm a link
        first_link_id = links[0]["id"]
        confirm_resp = await client.post(
            f"/api/v1/verification/projects/{project_id}/confirm-link/{first_link_id}",
            json={"is_confirmed": True},
        )
        assert confirm_resp.status_code == 200
        updated_link = confirm_resp.json()
        assert updated_link["is_confirmed"] is True
        assert "confirmed" in updated_link["link_type"]

        # 8. Trigger verification run
        run_resp = await client.post(
            f"/api/v1/verification/projects/{project_id}/runs",
            json={"specification_id": spec_id},
        )
        assert run_resp.status_code == 201
        run = run_resp.json()
        run_id = run["id"]
        assert run_id.startswith("run-")
        # Run status will be 'unavailable' (daemon stopped) or 'passed' (if docker running), never host crashed
        assert run["status"] in ["unavailable", "passed", "failed"]

        # 9. Get run details
        get_run_resp = await client.get(f"/api/v1/verification/runs/{run_id}")
        assert get_run_resp.status_code == 200
        assert get_run_resp.json()["id"] == run_id

        # 10. Get specification evidence
        evidence_resp = await client.get(
            f"/api/v1/requirements/specifications/{spec_id}/evidence?project_id={project_id}"
        )
        assert evidence_resp.status_code == 200
        evidence = evidence_resp.json()
        assert evidence["specification_id"] == spec_id
        assert "verdicts" in evidence
        assert len(evidence["verdicts"]) > 0
