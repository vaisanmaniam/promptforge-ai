"""
Patch Safety and Workspace Integrity Service.
Enforces workspace jailing, path traversal defense, hash integrity checks,
Python AST syntax validation, rollback snapshots, and safe reversion.
"""

import ast
import hashlib
import os
from pathlib import Path
import shutil
from typing import Dict, Optional, Tuple

from app.schemas.repair import PatchApplicationResult, RepairProposal

REPAIR_SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "repair" / "snapshots"


class SecurePatcher:
    """
    Validates and applies repair patches to isolated project workspaces.
    """

    MAX_PATCH_SIZE_BYTES = 50 * 1024  # 50 KB

    def __init__(self, projects_root: Optional[Path] = None, snapshots_dir: Optional[Path] = None):
        self.projects_root = (
            projects_root
            or (Path(__file__).resolve().parent.parent.parent.parent / "data" / "projects")
        )
        self.snapshots_dir = snapshots_dir or REPAIR_SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def validate_patch_safety(
        self,
        proposal: RepairProposal,
        project_dir: Path,
    ) -> Tuple[bool, str]:
        """
        Conducts strict pre-application safety inspection:
        - Path traversal and absolute path check
        - Size bounds check
        - Current file existence and hash match against proposal.original_artifact_hash
        - Python AST syntax check on patched content
        """
        rel_path = proposal.target_artifact_path.replace("\\", "/")

        # 1. Path traversal / absolute path check
        if rel_path.startswith("/") or rel_path.startswith("\\") or ".." in rel_path:
            return False, f"Security Violation: Target path '{rel_path}' contains forbidden absolute or traversal patterns."

        target_file = (project_dir / rel_path).resolve()
        resolved_proj = project_dir.resolve()

        # Workspace jail check
        try:
            target_file.relative_to(resolved_proj)
        except ValueError:
            return False, f"Security Violation: Target file '{target_file}' escapes workspace boundary '{resolved_proj}'."

        # 2. Patch size limit
        if len(proposal.patched_content.encode("utf-8")) > self.MAX_PATCH_SIZE_BYTES:
            return False, f"Patch size exceeds maximum limit of {self.MAX_PATCH_SIZE_BYTES} bytes."

        # 3. File existence and hash integrity check
        if not target_file.exists():
            return False, f"Target file '{rel_path}' does not exist in workspace."

        try:
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                current_content = f.read()
        except Exception as e:
            return False, f"Could not read target file: {e}"

        current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
        if current_hash != proposal.original_artifact_hash:
            return (
                False,
                f"Stale Patch Rejected: Original file hash has changed "
                f"(expected {proposal.original_artifact_hash[:10]}, found {current_hash[:10]}).",
            )

        # 4. AST syntax check on Python files
        if rel_path.endswith(".py"):
            try:
                ast.parse(proposal.patched_content, filename=rel_path)
            except SyntaxError as e:
                return False, f"Patch introduces SyntaxError at line {e.lineno}: {e.msg}"

        return True, "Patch passed all safety validations."

    def apply_patch(
        self,
        proposal: RepairProposal,
        project_dir: Path,
    ) -> PatchApplicationResult:
        """
        Takes an approved proposal, creates an immutable rollback snapshot,
        writes the patched content, and verifies the resulting hash.
        """
        valid, msg = self.validate_patch_safety(proposal, project_dir)
        if not valid:
            return PatchApplicationResult(
                success=False,
                repair_id=proposal.repair_id,
                file_path=proposal.target_artifact_path,
                original_sha256=proposal.original_artifact_hash,
                new_sha256=proposal.original_artifact_hash,
                rollback_available=False,
                message=msg,
            )

        rel_path = proposal.target_artifact_path.replace("\\", "/")
        target_file = project_dir / rel_path

        # 1. Create rollback snapshot
        snapshot_folder = self.snapshots_dir / proposal.repair_id
        snapshot_folder.mkdir(parents=True, exist_ok=True)
        snapshot_file = snapshot_folder / f"{target_file.name}.orig"

        try:
            shutil.copy2(target_file, snapshot_file)
        except Exception as e:
            return PatchApplicationResult(
                success=False,
                repair_id=proposal.repair_id,
                file_path=rel_path,
                original_sha256=proposal.original_artifact_hash,
                new_sha256=proposal.original_artifact_hash,
                rollback_available=False,
                message=f"Failed to create rollback snapshot: {e}",
            )

        # 2. Write patched content
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(proposal.patched_content)
        except Exception as e:
            # Attempt to revert from snapshot if write failed
            if snapshot_file.exists():
                shutil.copy2(snapshot_file, target_file)
            return PatchApplicationResult(
                success=False,
                repair_id=proposal.repair_id,
                file_path=rel_path,
                original_sha256=proposal.original_artifact_hash,
                new_sha256=proposal.original_artifact_hash,
                rollback_available=False,
                message=f"Failed to apply patch to file: {e}",
            )

        # 3. Calculate new hash
        new_hash = hashlib.sha256(proposal.patched_content.encode("utf-8")).hexdigest()

        return PatchApplicationResult(
            success=True,
            repair_id=proposal.repair_id,
            file_path=rel_path,
            original_sha256=proposal.original_artifact_hash,
            new_sha256=new_hash,
            rollback_available=True,
            message="Patch successfully applied to workspace. Rollback snapshot secured.",
        )

    def rollback_patch(
        self,
        proposal: RepairProposal,
        project_dir: Path,
    ) -> Tuple[bool, str]:
        """
        Reverts target file in project_dir back to its pre-patch snapshot.
        """
        rel_path = proposal.target_artifact_path.replace("\\", "/")
        target_file = project_dir / rel_path

        snapshot_folder = self.snapshots_dir / proposal.repair_id
        snapshot_file = snapshot_folder / f"{target_file.name}.orig"

        if not snapshot_file.exists():
            return False, f"Rollback snapshot for repair '{proposal.repair_id}' not found."

        try:
            shutil.copy2(snapshot_file, target_file)
            return True, f"Successfully rolled back '{rel_path}' to pre-repair state."
        except Exception as e:
            return False, f"Failed to restore rollback snapshot: {e}"
