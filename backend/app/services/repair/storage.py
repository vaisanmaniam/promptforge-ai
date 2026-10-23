"""
Repair Repository and Audit Trail Storage.
Provides hybrid persistence for failure diagnoses, repair proposals,
and immutable lifecycle audit records with local JSON fallback in backend/data/repair/.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.core.logging import logger
from app.db.session import check_database_health, get_async_engine
from app.models.repair import (
    FailureAnalysisModel,
    RepairAuditLogModel,
    RepairProposalModel,
)
from app.schemas.repair import (
    FailureAnalysisReport,
    RepairAuditLogEntry,
    RepairProposal,
)

REPAIR_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "repair"


class RepairRepository:
    """
    Persists and indexes failure diagnoses, proposals, and audit logs.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or REPAIR_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "failures").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "proposals").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "audit").mkdir(parents=True, exist_ok=True)

        self._failures_cache: Dict[str, FailureAnalysisReport] = {}
        self._proposals_cache: Dict[str, RepairProposal] = {}
        self._audit_cache: List[RepairAuditLogEntry] = []
        self._load_all()

    def _load_all(self) -> None:
        """Loads cached records from local JSON files."""
        # Failures
        f_dir = self.data_dir / "failures"
        for p in f_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rep = FailureAnalysisReport.model_validate(data)
                self._failures_cache[rep.failure_id] = rep
            except Exception:
                pass

        # Proposals
        p_dir = self.data_dir / "proposals"
        for p in p_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                prop = RepairProposal.model_validate(data)
                self._proposals_cache[prop.repair_id] = prop
            except Exception:
                pass

        # Audit
        a_file = self.data_dir / "audit" / "events.json"
        if a_file.exists():
            try:
                with open(a_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._audit_cache = [RepairAuditLogEntry.model_validate(d) for d in data]
            except Exception:
                pass

    def save_failure(self, report: FailureAnalysisReport) -> FailureAnalysisReport:
        """Saves a failure analysis report."""
        self._failures_cache[report.failure_id] = report
        file_path = self.data_dir / "failures" / f"{report.failure_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist failure JSON: {e}")
        return report

    def get_failure(self, failure_id: str) -> Optional[FailureAnalysisReport]:
        """Retrieves a failure analysis by failure_id."""
        return self._failures_cache.get(failure_id)

    def list_failures_for_run(self, run_id: str) -> List[FailureAnalysisReport]:
        """Lists all failures analyzed for a specific run_id."""
        return [f for f in self._failures_cache.values() if f.run_id == run_id]

    def save_proposal(self, proposal: RepairProposal) -> RepairProposal:
        """Saves or updates a repair proposal."""
        self._proposals_cache[proposal.repair_id] = proposal
        file_path = self.data_dir / "proposals" / f"{proposal.repair_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(proposal.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist proposal JSON: {e}")
        return proposal

    def get_proposal(self, repair_id: str) -> Optional[RepairProposal]:
        """Retrieves a repair proposal by repair_id."""
        return self._proposals_cache.get(repair_id)

    def list_proposals(self, project_id: Optional[str] = None) -> List[RepairProposal]:
        """Lists repair proposals, optionally filtered by project_id."""
        res = list(self._proposals_cache.values())
        if project_id:
            res = [p for p in res if p.project_id == project_id]
        return sorted(res, key=lambda x: x.created_at, reverse=True)

    def record_audit_event(
        self,
        repair_id: str,
        action: str,
        from_status: str,
        to_status: str,
        actor: str = "developer",
        details: Optional[Dict[str, Any]] = None,
    ) -> RepairAuditLogEntry:
        """Records an immutable lifecycle transition in the audit ledger."""
        now = datetime.now(timezone.utc).isoformat()
        entry = RepairAuditLogEntry(
            id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            repair_id=repair_id,
            action=action,
            actor=actor,
            from_status=from_status,
            to_status=to_status,
            timestamp=now,
            details=details or {},
        )
        self._audit_cache.append(entry)

        # Save audit log
        a_file = self.data_dir / "audit" / "events.json"
        try:
            with open(a_file, "w", encoding="utf-8") as f:
                json.dump([e.model_dump() for e in self._audit_cache], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to append audit event: {e}")

        return entry

    def get_audit_trail(self, repair_id: Optional[str] = None) -> List[RepairAuditLogEntry]:
        """Retrieves audit entries, optionally filtered by repair_id."""
        if repair_id:
            return [e for e in self._audit_cache if e.repair_id == repair_id]
        return sorted(self._audit_cache, key=lambda x: x.timestamp, reverse=True)
