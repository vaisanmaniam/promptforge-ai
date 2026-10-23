"""
Unit tests for Verification Engine.
Tests static AST analysis, test discovery, pytest output parsing,
truthful requirement verdict formulas, and fail-closed Docker unavailable behavior.
"""

from pathlib import Path
from unittest.mock import MagicMock
from app.schemas.requirement import (
    AcceptanceCriterion,
    RequirementCategory,
    RequirementItem,
    RequirementSpecification,
)
from app.schemas.verification import (
    ArtifactMetadata,
    ExecutionStatus,
    FileType,
    LinkOrigin,
    LinkType,
    RequirementVerdictStatus,
    TraceabilityLink,
)
from app.services.verification.docker_runner import DockerExecutionAdapter, ExecutionResult
from app.services.verification.engine import VerificationEngine


def test_static_inspection_and_test_discovery(tmp_path):
    """Verify AST static analysis identifies syntax errors and discovers test functions."""
    engine = VerificationEngine()

    good_src = tmp_path / "app.py"
    good_src.write_text("def run():\n    return 42\n")

    bad_src = tmp_path / "broken.py"
    bad_src.write_text("def syntax_error(\n")

    test_file = tmp_path / "test_app.py"
    test_file.write_text(
        "def test_one(): pass\n"
        "class TestSuite:\n"
        "    def test_two(self): pass\n"
    )

    artifacts = [
        ArtifactMetadata(
            id="A1", project_id="p1", relative_path="app.py",
            file_type=FileType.SOURCE_FILE, language="python", sha256="1", size_bytes=20, line_count=2, created_at="",
        ),
        ArtifactMetadata(
            id="A2", project_id="p1", relative_path="broken.py",
            file_type=FileType.SOURCE_FILE, language="python", sha256="2", size_bytes=20, line_count=1, created_at="",
        ),
        ArtifactMetadata(
            id="A3", project_id="p1", relative_path="test_app.py",
            file_type=FileType.TEST_FILE, language="python", sha256="3", size_bytes=50, line_count=3, created_at="",
        ),
    ]

    static_ok, findings = engine.run_static_inspection(tmp_path, artifacts)
    assert static_ok is False
    assert any("SyntaxError" in f for f in findings)

    discovered_tests = engine.discover_tests(tmp_path, artifacts)
    assert len(discovered_tests) == 2
    assert any("test_one" in t for t in discovered_tests)
    assert any("test_two" in t for t in discovered_tests)


def test_fail_closed_when_docker_unavailable(tmp_path):
    """Verify engine reports 'unavailable' and refuses host execution when Docker daemon is offline."""
    mock_runner = MagicMock(spec=DockerExecutionAdapter)
    mock_runner.check_docker_availability.return_value = (False, "Docker daemon is stopped.")
    mock_runner.run_pytest.return_value = ExecutionResult(
        success=False,
        exit_code=None,
        stdout="",
        stderr="",
        duration_ms=0.0,
        error_message="Execution blocked: Docker daemon is stopped. (Host fallback prohibited).",
    )

    engine = VerificationEngine(runner=mock_runner)

    run = engine.execute_verification(
        project_id="prj-test",
        project_dir=tmp_path,
        artifacts=[],
    )

    assert run.status == ExecutionStatus.UNAVAILABLE
    assert run.docker_available is False
    assert run.total_tests == 0


def test_requirement_verdict_formulas(tmp_path):
    """Verify requirement verification is granted only when tests pass, and denied when tests fail."""
    mock_runner = MagicMock(spec=DockerExecutionAdapter)
    mock_runner.check_docker_availability.return_value = (True, "Ready")
    mock_runner.run_pytest.return_value = ExecutionResult(
        success=False,
        exit_code=1,
        stdout=(
            "tests/test_auth.py::test_login PASSED\n"
            "tests/test_cache.py::test_evict FAILED\n"
            "=== 1 passed, 1 failed in 0.20s ===\n"
        ),
        stderr="",
        duration_ms=200.0,
    )

    engine = VerificationEngine(runner=mock_runner)

    req1 = RequirementItem(
        id="REQ-001",
        title="Authentication Gateway",
        description="Auth",
        category=RequirementCategory.SECURITY,
        acceptance_criteria=[AcceptanceCriterion(id="AC-1", description="Logs in.")],
    )
    req2 = RequirementItem(
        id="REQ-002",
        title="Cache Eviction",
        description="Evicts",
        category=RequirementCategory.FUNCTIONAL,
        acceptance_criteria=[AcceptanceCriterion(id="AC-2", description="Evicts.")],
    )
    req3 = RequirementItem(
        id="REQ-003",
        title="Untested Feature",
        description="No tests",
        category=RequirementCategory.FUNCTIONAL,
        acceptance_criteria=[AcceptanceCriterion(id="AC-3", description="Works.")],
    )

    spec = RequirementSpecification(
        id="spec-v",
        title="Verdicts Spec",
        source_prompt="test",
        requirements=[req1, req2, req3],
        assumptions=[],
        created_at="",
        updated_at="",
    )

    links = [
        TraceabilityLink(
            id="L1", project_id="p1", specification_id="spec-v", requirement_id="REQ-001",
            artifact_path="tests/test_auth.py", symbol_name="test_login",
            link_type=LinkType.CANDIDATE_TEST, link_origin=LinkOrigin.STATIC_ANALYSIS,
            confidence=0.9, is_confirmed=True, rationale="", created_at="",
        ),
        TraceabilityLink(
            id="L2", project_id="p1", specification_id="spec-v", requirement_id="REQ-002",
            artifact_path="tests/test_cache.py", symbol_name="test_evict",
            link_type=LinkType.CANDIDATE_TEST, link_origin=LinkOrigin.STATIC_ANALYSIS,
            confidence=0.9, is_confirmed=True, rationale="", created_at="",
        ),
    ]

    run = engine.execute_verification(
        project_id="p1",
        project_dir=tmp_path,
        artifacts=[],
        spec=spec,
        links=links,
    )

    assert run.status == ExecutionStatus.FAILED
    assert run.total_tests == 2
    assert run.passed_tests == 1
    assert run.failed_tests == 1

    verdicts = run.requirement_verdicts
    assert verdicts["REQ-001"].verdict == RequirementVerdictStatus.VERIFIED
    assert verdicts["REQ-002"].verdict == RequirementVerdictStatus.FAILED
    assert verdicts["REQ-003"].verdict == RequirementVerdictStatus.UNVERIFIED

    # Check evidence report
    evidence = engine.build_evidence_report(spec=spec, links=links, latest_run=run)
    assert evidence.verified_requirement_count == 1
    assert evidence.failed_requirement_count == 1
    assert evidence.unverified_requirement_count == 1
    assert evidence.verification_coverage_pct == 33.3  # 1 of 3 verified
