import pytest
from app.db.session import check_database_health


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_postgresql_connection():
    """
    Integration test against actual PostgreSQL instance.
    Runs when Docker/PostgreSQL is actually reachable; otherwise skips cleanly.
    Never uses mocks to pretend an offline database is online.
    """
    is_healthy, message, latency_ms = await check_database_health()
    if not is_healthy:
        pytest.skip(
            f"PostgreSQL service is currently unreachable ({message}). "
            "To execute this live integration test, start the database with: "
            "'docker compose up -d postgres'."
        )

    assert is_healthy is True
    assert "SELECT 1" in message
    assert latency_ms > 0
