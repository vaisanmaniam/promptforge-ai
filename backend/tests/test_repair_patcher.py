"""
Unit tests for Secure Patch Application and Rollback Service (Phase 6).
Tests workspace jail enforcement, path traversal defense, hash integrity validation,
AST syntax verification, and snapshot-backed rollback.
"""

import hashlib
from pathlib import Path
import pytest

from app.schemas.repair import RepairCandidateStatus, RepairProposal, RiskLevel
from app.services.repair.patcher import SecurePatcher


@pytest.fixture
def patch_env(tmp_path):
    project_dir = tmp_path / "workspace"
    project_dir.mkdir(parents=True, exist_ok=True)
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    src_file = project_dir / "calculator.py"
    initial_code = "def subtract(a, b):\n    return a + b\n"
    src_file.write_text(initial_code, encoding="utf-8")
    initial_sha = hashlib.sha256(initial_code.encode("utf-8")).hexdigest()

    patcher = SecurePatcher(snapshots_dir=snapshots_dir)

    proposal = RepairProposal(
        repair_id="REP-TEST-001",
        failure_ids=["FAIL-1"],
        project_id="proj-jail",
        target_artifact_path="calculator.py",
        original_artifact_hash=initial_sha,
        original_content=initial_code,
        patched_content="def subtract(a, b):\n    return a - b\n",
        unified_diff="--- calculator.py\n+++ calculator.py\n@@ -2,1 +2,1 @@\n-    return a + b\n+    return a - b\n",
        explanation="Fixed addition operator to subtraction.",
        status=RepairCandidateStatus.APPROVED,
        risk_level=RiskLevel.LOW,
        generator_type="deterministic_rule_engine",
        created_at="",
    )

    return patcher, project_dir, proposal, src_file, initial_sha, snapshots_dir


def test_jail_path_traversal_blocked(patch_env):
    patcher, project_dir, proposal, src_file, _, _ = patch_env

    # Malicious path attempting to escape jail
    proposal.target_artifact_path = "../../etc/passwd"
    is_safe, msg = patcher.validate_patch_safety(proposal, project_dir)
    assert is_safe is False
    assert "Security Violation" in msg

    proposal.target_artifact_path = "..\\..\\windows\\system32"
    is_safe2, msg2 = patcher.validate_patch_safety(proposal, project_dir)
    assert is_safe2 is False
    assert "Security Violation" in msg2


def test_stale_hash_mismatch_rejected(patch_env):
    patcher, project_dir, proposal, src_file, _, _ = patch_env

    # Externally modify file so hash drifts
    src_file.write_text("def subtract(a, b):\n    return 42\n", encoding="utf-8")

    result = patcher.apply_patch(proposal, project_dir)
    assert result.success is False
    assert "hash has changed" in result.message.lower()
    assert "stale" in result.message.lower()


def test_syntax_error_in_patch_rejected(patch_env):
    patcher, project_dir, proposal, src_file, _, _ = patch_env

    # Broken syntax in proposed patched_content
    proposal.patched_content = "def broken_code(\n    syntax error here\n"

    result = patcher.apply_patch(proposal, project_dir)
    assert result.success is False
    assert "SyntaxError" in result.message

    # Ensure original file was NOT touched
    assert "return a + b" in src_file.read_text(encoding="utf-8")


def test_successful_patch_and_rollback(patch_env):
    patcher, project_dir, proposal, src_file, initial_sha, snapshots_dir = patch_env

    # 1. Apply valid patch
    result = patcher.apply_patch(proposal, project_dir)
    assert result.success is True
    assert result.rollback_available is True
    assert src_file.read_text(encoding="utf-8") == "def subtract(a, b):\n    return a - b\n"

    # Verify snapshot was created on disk
    snapshot_file = snapshots_dir / proposal.repair_id / "calculator.py.orig"
    assert snapshot_file.exists()
    assert snapshot_file.read_text(encoding="utf-8") == proposal.original_content

    # 2. Rollback patch
    rb_success, rb_msg = patcher.rollback_patch(proposal, project_dir)
    assert rb_success is True
    assert "Successfully rolled back" in rb_msg

    # Verify file is restored to initial content
    restored_code = src_file.read_text(encoding="utf-8")
    assert restored_code == "def subtract(a, b):\n    return a + b\n"
    assert hashlib.sha256(restored_code.encode("utf-8")).hexdigest() == initial_sha
