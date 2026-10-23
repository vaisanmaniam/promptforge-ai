"""
Pydantic Schemas for Failure-Guided Automated Code Repair Engine.
Defines failure classifications, ranked hypotheses, repair proposals, unified diff representations,
patch application results, before-and-after verification comparisons, and immutable audit logs.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FailureCategory(str, Enum):
    """Categorization of verification execution failures."""
    ASSERTION_FAILURE = "assertion_failure"
    EXCEPTION = "exception"
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    STATIC_ANALYSIS_VIOLATION = "static_analysis_violation"
    TIMEOUT = "timeout"
    ENVIRONMENT_BLOCKED = "environment_blocked"
    UNKNOWN = "unknown"


class DefectClassification(str, Enum):
    """Classification of root cause origin."""
    CODE_DEFECT = "code_defect"
    TEST_DEFECT = "test_defect"
    ENVIRONMENT_ISSUE = "environment_issue"
    UNRESOLVED = "unresolved"


class RepairCandidateStatus(str, Enum):
    """Lifecycle progression of a code repair candidate."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED_VERIFICATION = "failed_verification"
    ROLLED_BACK = "rolled_back"
    STALE = "stale"
    BLOCKED = "blocked"


class RiskLevel(str, Enum):
    """Assessed risk of applying a proposed repair."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SECURITY_RESTRICTED = "security_restricted"


class FailureHypothesis(BaseModel):
    """Evidence-backed hypothesis for a specific failure."""
    rank: int = Field(ge=1, description="Ranking priority of hypothesis")
    description: str = Field(description="Human-readable explanation of suspected root cause")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score backed by parsed evidence")
    evidence_basis: str = Field(description="Concrete evidence from traceback, AST, or assertion diff")
    suspected_file: Optional[str] = None
    suspected_line: Optional[int] = None


class FailureAnalysisReport(BaseModel):
    """Comprehensive failure diagnosis derived from real verification run logs."""
    failure_id: str = Field(description="Stable failure ID, e.g. FAIL-001")
    run_id: str = Field(description="Verification run ID where failure occurred")
    project_id: str
    test_id: str = Field(description="Failing test node ID, e.g. tests/test_calc.py::test_subtract")
    category: FailureCategory
    classification: DefectClassification
    traceback_excerpt: str
    suspected_file: Optional[str] = None
    suspected_line: Optional[int] = None
    related_requirement_ids: List[str] = Field(default_factory=list)
    hypotheses: List[FailureHypothesis] = Field(default_factory=list)
    created_at: str


class RepairProposal(BaseModel):
    """Reviewable repair candidate containing unified diff and lifecycle metadata."""
    repair_id: str = Field(description="Stable repair ID, e.g. REP-001")
    failure_ids: List[str] = Field(default_factory=list)
    project_id: str
    target_artifact_path: str
    original_artifact_hash: str = Field(description="SHA-256 fingerprint before patch")
    patched_artifact_hash: Optional[str] = None
    original_content: Optional[str] = None
    patched_content: str
    unified_diff: str
    explanation: str
    status: RepairCandidateStatus = RepairCandidateStatus.PROPOSED
    risk_level: RiskLevel = RiskLevel.LOW
    generator_type: str = Field(description="'deterministic_rule_engine' or 'local_code_model'")
    related_requirement_ids: List[str] = Field(default_factory=list)
    related_test_ids: List[str] = Field(default_factory=list)
    created_at: str
    approved_at: Optional[str] = None
    applied_at: Optional[str] = None
    verified_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class PatchApplicationResult(BaseModel):
    """Result of safely applying a patch to the project workspace."""
    success: bool
    repair_id: str
    file_path: str
    original_sha256: str
    new_sha256: str
    rollback_available: bool = True
    message: str


class RepairVerificationComparison(BaseModel):
    """Before-and-after test execution verification audit."""
    repair_id: str
    pre_run_id: str
    post_run_id: str
    pre_failures_count: int
    post_failures_count: int
    fixed_test_ids: List[str] = Field(default_factory=list)
    new_failure_test_ids: List[str] = Field(default_factory=list)
    verification_status: RepairCandidateStatus
    rationale: str


class RepairAuditLogEntry(BaseModel):
    """Immutable audit record for a repair lifecycle event."""
    id: str = Field(description="Unique audit event ID, e.g. AUD-001")
    repair_id: str
    action: str
    actor: str = "developer"
    from_status: str
    to_status: str
    timestamp: str
    details: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------------------
# Request Payloads
# -------------------------------------------------------------------------

class GenerateProposalRequest(BaseModel):
    """Payload to trigger repair candidate generation for a failure."""
    failure_id: str
    generator_override: Optional[str] = None


class ProposalDecisionRequest(BaseModel):
    """Payload to approve or reject a repair proposal."""
    decision_reason: Optional[str] = None
