"""
Unit tests for Repair Strategy and Candidate Generation Service (Phase 6).
Tests deterministic rule engine, operator inversion, boundary fixes,
unified diff generation, and security-restricted path gating.
"""

from pathlib import Path
import pytest

from app.schemas.repair import (
    DefectClassification,
    FailureAnalysisReport,
    FailureCategory,
    FailureHypothesis,
    RepairCandidateStatus,
    RiskLevel,
)
from app.schemas.verification import ArtifactMetadata, FileType, ProjectIngestionReport
from app.services.repair.generator import RepairCandidateGenerator


@pytest.fixture
def sample_project(tmp_path):
    proj_dir = tmp_path / "project_root"
    proj_dir.mkdir(parents=True, exist_ok=True)

    calc_file = proj_dir / "calc.py"
    calc_file.write_text("def subtract(a, b):\n    return a + b\n")

    return ProjectIngestionReport(
        project_id="proj-calc",
        name="Calculator",
        total_files=1,
        total_size_bytes=35,
        ingested_artifacts=[
            ArtifactMetadata(
                id="art-1",
                project_id="proj-calc",
                relative_path="calc.py",
                file_type=FileType.SOURCE_FILE,
                language="python",
                sha256="abc123sha",
                size_bytes=35,
                line_count=2,
                created_at="",
            )
        ],
        ingested_at="",
    ), proj_dir


def test_generator_deterministic_operator_inversion(sample_project):
    project, proj_dir = sample_project
    generator = RepairCandidateGenerator(projects_dir=proj_dir.parent)

    failure = FailureAnalysisReport(
        failure_id="FAIL-01",
        run_id="RUN-01",
        project_id=project.project_id,
        test_id="tests/test_calc.py::test_subtract",
        category=FailureCategory.ASSERTION_FAILURE,
        classification=DefectClassification.CODE_DEFECT,
        traceback_excerpt="assert subtract(5, 3) == 2\nassert 8 == 2",
        suspected_file="calc.py",
        suspected_line=2,
        related_requirement_ids=["REQ-1"],
        hypotheses=[
            FailureHypothesis(
                rank=1,
                description="Incorrect operator: returned 8 instead of expected 2",
                confidence=0.85,
                evidence_basis="assert 8 == 2",
                suspected_file="calc.py",
                suspected_line=2,
            )
        ],
        created_at="",
    )

    proposal = generator.generate_repair_proposal(
        failure=failure,
        project=project,
        project_dir=proj_dir,
    )

    assert proposal is not None
    assert proposal.status == RepairCandidateStatus.PROPOSED
    assert proposal.target_artifact_path == "calc.py"
    assert "return a - b" in proposal.patched_content
    assert proposal.generator_type == "deterministic_rule_engine"
    assert "@@" in proposal.unified_diff
    assert "-    return a + b" in proposal.unified_diff
    assert "+    return a - b" in proposal.unified_diff
    assert proposal.risk_level == RiskLevel.LOW


def test_generator_boundary_inequality(tmp_path):
    proj_dir = tmp_path / "boundary_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)

    auth_file = proj_dir / "validator.py"
    auth_file.write_text("def check_age(age):\n    return age > 18\n")

    project = ProjectIngestionReport(
        project_id="proj-boundary",
        name="Boundary Service",
        total_files=1,
        total_size_bytes=35,
        ingested_artifacts=[
            ArtifactMetadata(
                id="art-2",
                project_id="proj-boundary",
                relative_path="validator.py",
                file_type=FileType.SOURCE_FILE,
                language="python",
                sha256="boundary-sha",
                size_bytes=35,
                line_count=2,
                created_at="",
            )
        ],
        ingested_at="",
    )

    generator = RepairCandidateGenerator(projects_dir=proj_dir.parent)

    failure = FailureAnalysisReport(
        failure_id="FAIL-02",
        run_id="RUN-02",
        project_id=project.project_id,
        test_id="tests/test_val.py::test_boundary",
        category=FailureCategory.ASSERTION_FAILURE,
        classification=DefectClassification.CODE_DEFECT,
        traceback_excerpt="assert check_age(18) is True\nassert False is True",
        suspected_file="validator.py",
        suspected_line=2,
        related_requirement_ids=[],
        hypotheses=[],
        created_at="",
    )

    proposal = generator.generate_repair_proposal(
        failure=failure,
        project=project,
        project_dir=proj_dir,
    )

    assert proposal is not None
    assert "age >= 18" in proposal.patched_content


def test_generator_security_restricted_path(tmp_path):
    proj_dir = tmp_path / "sec_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)

    token_file = proj_dir / "auth_tokens.py"
    token_file.write_text("def verify_token(t):\n    return t == 'secret'\n")

    project = ProjectIngestionReport(
        project_id="proj-sec",
        name="Security App",
        total_files=1,
        total_size_bytes=45,
        ingested_artifacts=[
            ArtifactMetadata(
                id="art-sec",
                project_id="proj-sec",
                relative_path="auth_tokens.py",
                file_type=FileType.SOURCE_FILE,
                language="python",
                sha256="sec-sha",
                size_bytes=45,
                line_count=2,
                created_at="",
            )
        ],
        ingested_at="",
    )

    generator = RepairCandidateGenerator(projects_dir=proj_dir.parent)

    failure = FailureAnalysisReport(
        failure_id="FAIL-SEC",
        run_id="RUN-SEC",
        project_id=project.project_id,
        test_id="tests/test_sec.py::test_token",
        category=FailureCategory.ASSERTION_FAILURE,
        classification=DefectClassification.CODE_DEFECT,
        traceback_excerpt="assert verify_token('invalid') is False",
        suspected_file="auth_tokens.py",
        suspected_line=2,
        related_requirement_ids=[],
        hypotheses=[],
        created_at="",
    )

    proposal = generator.generate_repair_proposal(
        failure=failure,
        project=project,
        project_dir=proj_dir,
    )

    if proposal:
        assert proposal.risk_level == RiskLevel.SECURITY_RESTRICTED
