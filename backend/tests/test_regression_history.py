"""
Unit tests for Test History Repository.
Verifies observation extraction from verification runs, failure frequency calculations,
and deduplication.
"""

import pytest
from app.schemas.verification import (
    ExecutionStatus,
    RequirementEvidenceVerdict,
    RequirementVerdictStatus,
    VerificationRun,
)
from app.services.regression.history import TestHistoryRepository


def test_history_records_verification_run(tmp_path):
    """Verify observations are extracted correctly from a completed VerificationRun."""
    repo = TestHistoryRepository(data_dir=tmp_path)

    run = VerificationRun(
        id="RUN-TEST-001",
        project_id="PROJ-001",
        status=ExecutionStatus.FAILED,
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
        requirement_verdicts={
            "REQ-001": RequirementEvidenceVerdict(
                requirement_id="REQ-001",
                requirement_title="Calculator Add",
                verdict=RequirementVerdictStatus.FAILED,
                linked_code_count=1,
                linked_test_count=1,
                passed_tests=["tests/test_calc.py::test_subtract"],
                failed_tests=["tests/test_calc.py::test_add"],
                rationale="Failed",
            )
        },
        created_at="2026-10-10T00:00:00Z",
    )

    new_obs = repo.record_verification_run(run)
    assert len(new_obs) == 2

    # Check stats for failed test
    has_hist, fail_rate, _ = repo.get_test_stats("tests/test_calc.py::test_add")
    assert has_hist is True
    assert fail_rate == 1.0

    # Check stats for passed test
    has_hist2, fail_rate2, _ = repo.get_test_stats("tests/test_calc.py::test_subtract")
    assert has_hist2 is True
    assert fail_rate2 == 0.0

    # Summary
    summary = repo.get_summary(project_id="PROJ-001")
    assert summary.total_observations == 2
    assert summary.failed_count == 1
    assert summary.passed_count == 1
    assert summary.has_genuine_failures is True
