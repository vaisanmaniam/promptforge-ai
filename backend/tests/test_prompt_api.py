import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_prompt_endpoint_success(client: AsyncClient):
    """Verify POST /api/v1/prompts/analyze returns full diagnostic report."""
    payload = {
        "prompt": "Implement a thread-safe LRU cache in Python with O(1) time complexity."
    }
    response = await client.post("/api/v1/prompts/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "task_classification" in data
    assert data["task_classification"]["predicted_category"] == "code_generation"
    assert "components" in data
    assert "objective" in data["components"]["detected"]
    assert "ambiguity" in data
    assert "quality" in data
    assert data["quality"]["overall_score"] > 50.0
    assert "token_count" in data
    assert data["token_count"] > 0


@pytest.mark.asyncio
async def test_analyze_prompt_category_override(client: AsyncClient):
    """Verify user category override is respected."""
    payload = {
        "prompt": "Implement something in Python",
        "task_category": "api_development",
    }
    response = await client.post("/api/v1/prompts/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["task_classification"]["predicted_category"] == "api_development"
    assert data["task_classification"]["method"] == "user_override"


@pytest.mark.asyncio
async def test_analyze_prompt_validation_failure(client: AsyncClient):
    """Verify empty prompt returns 422 Unprocessable Entity."""
    response = await client.post("/api/v1/prompts/analyze", json={"prompt": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_optimize_prompt_endpoint_success(client: AsyncClient):
    """Verify POST /api/v1/prompts/optimize generates structured output and before/after comparisons."""
    payload = {
        "prompt": "Create an API endpoint to register users."
    }
    response = await client.post("/api/v1/prompts/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "optimization" in data
    opt = data["optimization"]
    assert "Create an API endpoint to register users." in opt["optimized_prompt"]
    assert len(opt["added_sections"]) >= 4
    assert len(opt["assumptions"]) > 0

    assert "original_quality" in data
    assert "optimized_quality" in data
    assert data["optimized_quality"]["overall_score"] >= data["original_quality"]["overall_score"]

    assert "token_analysis" in data
    assert data["token_analysis"]["optimized_tokens"] > data["token_analysis"]["original_tokens"]


@pytest.mark.asyncio
async def test_optimize_prompt_validation_failure(client: AsyncClient):
    """Verify empty optimization request returns 422."""
    response = await client.post("/api/v1/prompts/optimize", json={"prompt": ""})
    assert response.status_code == 422
