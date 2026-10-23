"""
Integration test for real Docker sandbox execution.
Skips cleanly if the Docker daemon is stopped, but runs genuine containerized tests
whenever Docker is operational.
"""

import pytest
from app.services.verification.docker_runner import DockerExecutionAdapter

adapter = DockerExecutionAdapter()
is_docker_ready, docker_status_message = adapter.check_docker_availability()


@pytest.mark.docker
@pytest.mark.skipif(
    not is_docker_ready,
    reason=f"Real Docker execution skipped: {docker_status_message}",
)
def test_real_docker_container_execution(tmp_path):
    """
    Genuine Docker container execution test.
    Only executes if the Docker engine daemon is genuinely reachable.
    """
    # Create a small valid pytest project in temp workspace
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_truth():\n    assert 1 + 1 == 2\n")

    result = adapter.run_pytest(
        project_dir=tmp_path,
        test_command=["pytest", "-v"],
    )

    assert result.success is True
    assert result.exit_code == 0
    assert "1 passed" in result.stdout
    assert result.duration_ms > 0
