"""
Unit tests for Failure Analysis Service (Phase 6).
Tests parsing pytest failures, assertion diffs, exception tracebacks, static findings,
linkage to requirements, and strict separation of environment obstacles from code defects.
"""

from pathlib import Path
import pytest

from app.schemas.repair import DefectClassification, FailureCategory
from app.schemas.verification import (
    ArtifactMetadata,
    ExecutionStatus,
    FileType,
    LinkOrigin,
    LinkType,
    TraceabilityLink,
    VerificationRun,
)
from app.services.repair.failure_analyzer import FailureAnalyzer


def test_analyze_assertion_failure(tmp_path):
    """Test parsing a pytest assertion failure into structured hypotheses."""
    analyzer = FailureAnalyzer()

    # Create dummy source and test artifacts
    src_file = tmp_path / "calc.py"
    src_file.write_text("def subtract(a, b):\n    return a + b\n")

    test_file = tmp_path / "tests" / "test_calc.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("from calc import subtract\ndef test_subtract():\n    assert subtract(5, 3) == 2\n")

    artifacts = [
        ArtifactMetadata(
            id="art-src",
            project_id="proj-1",
            relative_path="calc.py",
            file_type=FileType.SOURCE_FILE,
            language="python",
            sha256="sha-1",
            size_bytes=40,
            line_count=2,
            created_at="",
        ),
        ArtifactMetadata(
            id="art-test",
            project_id="proj-1",
            relative_path="tests/test_calc.py",
            file_type=FileType.TEST_FILE,
            language="python",
            sha256="sha-2",
            size_bytes=80,
            line_count=3,
            created_at="",
        ),
    ]

    links = [
        TraceabilityLink(
            id="link-1",
            project_id="proj-1",
            specification_id="spec-1",
            requirement_id="REQ-001",
            artifact_path="calc.py",
            symbol_name="subtract",
            link_type=LinkType.CONFIRMED_IMPLEMENTATION,
            link_origin=LinkOrigin.STATIC_ANALYSIS,
            confidence=0.9,
            rationale="Implements subtract",
            created_at="",
        )
    ]

    stdout = """
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

    run = VerificationRun(
        id="run-1",
        project_id="proj-1",
        status=ExecutionStatus.FAILED,
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        stdout=stdout,
        stderr="",
        duration_ms=50.0,
        created_at="",
    )

    reports = analyzer.analyze_run_failures(run=run, artifacts=artifacts, links=links)
    assert len(reports) == 1
    report = reports[0]

    assert report.category == FailureCategory.ASSERTION_FAILURE
    assert report.classification == DefectClassification.CODE_DEFECT
    assert "test_subtract" in report.test_id
    assert report.suspected_file == "calc.py"
    assert "REQ-001" in report.related_requirement_ids
    assert len(report.hypotheses) >= 1
    assert report.hypotheses[0].rank == 1
    assert report.hypotheses[0].confidence > 0.5


def test_analyze_exception_failure(tmp_path):
    """Test parsing an unhandled ZeroDivisionError traceback."""
    analyzer = FailureAnalyzer()

    src_file = tmp_path / "math_ops.py"
    src_file.write_text("def divide(a, b):\n    return a / b\n")

    artifacts = [
        ArtifactMetadata(
            id="art-math",
            project_id="proj-2",
            relative_path="math_ops.py",
            file_type=FileType.SOURCE_FILE,
            language="python",
            sha256="sha-math",
            size_bytes=35,
            line_count=2,
            created_at="",
        )
    ]

    stdout = """
=================================== FAILURES ===================================
_________________________________ test_divide __________________________________

    def test_divide():
>       divide(10, 0)

tests/test_math.py:3: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
math_ops.py:2: in divide
    return a / b
E   ZeroDivisionError: division by zero
=========================== short test summary info ============================
FAILED tests/test_math.py::test_divide - ZeroDivisionError: division by zero
"""

    run = VerificationRun(
        id="run-2",
        project_id="proj-2",
        status=ExecutionStatus.FAILED,
        total_tests=1,
        passed_tests=0,
        failed_tests=1,
        stdout=stdout,
        stderr="",
        duration_ms=45.0,
        created_at="",
    )

    reports = analyzer.analyze_run_failures(run=run, artifacts=artifacts, links=[])
    assert len(reports) == 1
    report = reports[0]

    assert report.category == FailureCategory.EXCEPTION
    assert report.classification == DefectClassification.CODE_DEFECT
    assert "ZeroDivisionError" in report.traceback_excerpt
    assert report.suspected_file == "math_ops.py"
    assert report.suspected_line == 2


def test_analyze_environment_blocked_never_code_defect():
    """Verify Docker sandbox unavailability is strictly classified as environment issue."""
    analyzer = FailureAnalyzer()

    run = VerificationRun(
        id="run-env",
        project_id="proj-env",
        status=ExecutionStatus.UNAVAILABLE,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        stdout="",
        stderr="Docker daemon is not running. Sandbox unavailable.",
        duration_ms=0.0,
        created_at="",
    )

    reports = analyzer.analyze_run_failures(run=run, artifacts=[], links=[])
    assert len(reports) == 1
    report = reports[0]

    assert report.category == FailureCategory.ENVIRONMENT_BLOCKED
    assert report.classification == DefectClassification.ENVIRONMENT_ISSUE
    assert report.suspected_file is None
    assert "Docker" in report.hypotheses[0].description
