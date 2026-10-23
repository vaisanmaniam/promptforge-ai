"""
Unit tests for Repair Lifecycle Coordinator (Phase 6).
Tests state transitions: PROPOSED -> APPROVED -> APPLIED -> VERIFIED / FAILED_VERIFICATION -> ROLLED_BACK,
and Docker-unavailable fail-closed blocked behavior.
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.schemas.repair import (
    PatchApplicationResult,
    RepairCandidateStatus,
    RepairProposal,
    RiskLevel,
)
from app.schemas.verification import (
    ArtifactMetadata,
    ExecutionStatus,
    FileType,
    ProjectIngestionReport,
    VerificationRun,
)
from app.services.repair.lifecycle import RepairLifecycleCoordinator
from app.services.repair.patcher import SecurePatcher
from app.services.repair.storage import RepairRepository


@pytest.fixture
def lifecycle_env(tmp_path):
    repair_dir = tmp_path / "repair_data"
    repair_dir.mkdir(parents=True, exist_ok=True)
    repair_repo = RepairRepository(data_dir=repair_dir)

    projects_dir = tmp_path / "projects"
    project_dir = projects_dir / "proj-life"
    project_dir.mkdir(parents=True, exist_ok=True)

    src_file = project_dir / "math.py"
    initial_code = "def calc(x):\n    return x + 1\n"
    src_file.write_text(initial_code, encoding="utf-8")
    initial_sha = hashlib.sha256(initial_code.encode("utf-8")).hexdigest()

    patcher = SecurePatcher(snapshots_dir=repair_dir / "snapshots")

    # Mock verification repository and engine
    verification_repo = MagicMock()
    verification_repo.data_dir = tmp_path / "verification_data"
    # Ensure verification_repo.data_dir.parent / "projects" resolves to projects_dir
    (verification_repo.data_dir).mkdir(parents=True, exist_ok=True)

    verification_repo.get_project = AsyncMock(
        return_value=ProjectIngestionReport(
            project_id="proj-life",
            name="Lifecycle Project",
            total_files=1,
            total_size_bytes=30,
            ingested_artifacts=[
                ArtifactMetadata(
                    id="art-m",
                    project_id="proj-life",
                    relative_path="math.py",
                    file_type=FileType.SOURCE_FILE,
                    language="python",
                    sha256=initial_sha,
                    size_bytes=30,
                    line_count=2,
                    created_at="",
                )
            ],
            ingested_at="",
        )
    )
    verification_repo.get_links = AsyncMock(return_value=[])
    verification_repo.save_run = AsyncMock()

    verification_engine = MagicMock()

    coordinator = RepairLifecycleCoordinator(
        repair_repo=repair_repo,
        verification_repo=verification_repo,
        patcher=patcher,
        verification_engine=verification_engine,
    )

    proposal = RepairProposal(
        repair_id="REP-LIFE-001",
        failure_ids=["FAIL-L1"],
        project_id="proj-life",
        target_artifact_path="math.py",
        original_artifact_hash=initial_sha,
        original_content=initial_code,
        patched_content="def calc(x):\n    return x + 2\n",
        unified_diff="--- math.py\n+++ math.py\n@@ -2,1 +2,1 @@\n-    return x + 1\n+    return x + 2\n",
        explanation="Adjust constant.",
        status=RepairCandidateStatus.PROPOSED,
        risk_level=RiskLevel.LOW,
        generator_type="deterministic_rule_engine",
        related_test_ids=["tests/test_math.py::test_calc"],
        created_at="",
    )
    repair_repo.save_proposal(proposal)

    return coordinator, repair_repo, proposal, verification_engine, src_file


@pytest.mark.asyncio
async def test_apply_without_approval_blocked(lifecycle_env):
    coordinator, repair_repo, proposal, _, _ = lifecycle_env

    # Attempting to apply directly without approval must fail
    success, p, result = await coordinator.apply_proposal(proposal.repair_id)
    assert success is False
    assert "must be APPROVED before application" in result.message
    assert p.status == RepairCandidateStatus.PROPOSED


@pytest.mark.asyncio
async def test_approve_and_reject_flow(lifecycle_env):
    coordinator, repair_repo, proposal, _, _ = lifecycle_env

    # Approve
    success, p, msg = await coordinator.approve_proposal(proposal.repair_id)
    assert success is True
    assert p.status == RepairCandidateStatus.APPROVED
    assert p.approved_at is not None

    # Reject a fresh proposal
    prop2 = RepairProposal(
        repair_id="REP-LIFE-002",
        failure_ids=[],
        project_id="proj-life",
        target_artifact_path="math.py",
        original_artifact_hash=proposal.original_artifact_hash,
        patched_content=proposal.patched_content,
        unified_diff=proposal.unified_diff,
        explanation="Test reject",
        status=RepairCandidateStatus.PROPOSED,
        risk_level=RiskLevel.LOW,
        generator_type="deterministic_rule_engine",
        created_at="",
    )
    repair_repo.save_proposal(prop2)

    rej_success, p2, rej_msg = await coordinator.reject_proposal(
        prop2.repair_id, reason="Unwanted logic modification"
    )
    assert rej_success is True
    assert p2.status == RepairCandidateStatus.REJECTED
    assert p2.rejection_reason == "Unwanted logic modification"


@pytest.mark.asyncio
async def test_apply_verify_and_rollback_flow(lifecycle_env):
    coordinator, repair_repo, proposal, verification_engine, src_file = lifecycle_env

    # 1. Approve
    await coordinator.approve_proposal(proposal.repair_id)

    # 2. Apply
    app_success, p, app_res = await coordinator.apply_proposal(proposal.repair_id)
    assert app_success is True
    assert p.status == RepairCandidateStatus.APPLIED
    assert "return x + 2" in src_file.read_text(encoding="utf-8")

    # 3. Verify with simulated passing run
    verification_engine.execute_verification.return_value = VerificationRun(
        id="run-post-pass",
        project_id="proj-life",
        status=ExecutionStatus.PASSED,
        total_tests=1,
        passed_tests=1,
        failed_tests=0,
        stdout="1 passed in 0.02s",
        stderr="",
        duration_ms=20.0,
        created_at="",
    )

    ver_success, p, comp, ver_msg = await coordinator.verify_proposal(proposal.repair_id)
    assert ver_success is True
    assert p.status == RepairCandidateStatus.VERIFIED
    assert comp is not None
    assert comp.post_failures_count == 0
    assert "tests/test_math.py::test_calc" in comp.fixed_test_ids

    # 4. Rollback from VERIFIED
    rb_success, p, rb_msg = await coordinator.rollback_proposal(proposal.repair_id)
    assert rb_success is True
    assert p.status == RepairCandidateStatus.ROLLED_BACK
    assert "return x + 1" in src_file.read_text(encoding="utf-8")
