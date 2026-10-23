"""
Pydantic schemas for Code Evidence & Automated Verification Engine.
Defines strongly typed models for ingested source artifacts, requirement-to-code traceability links,
Docker verification runs, and truthful requirement evidence metrics.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Classification of ingested project files."""
    SOURCE_FILE = "source_file"
    TEST_FILE = "test_file"
    MANIFEST = "manifest"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class LinkType(str, Enum):
    """Semantic status of a requirement traceability link."""
    CANDIDATE_IMPLEMENTATION = "candidate_implementation"
    CONFIRMED_IMPLEMENTATION = "confirmed_implementation"
    CANDIDATE_TEST = "candidate_test"
    CONFIRMED_TEST = "confirmed_test"


class LinkOrigin(str, Enum):
    """Method utilized to establish traceability link."""
    STATIC_ANALYSIS = "static_analysis"
    HEURISTIC_INFERENCE = "heuristic_inference"
    DEVELOPER_CONFIRMATION = "developer_confirmation"


class ExecutionStatus(str, Enum):
    """Lifecycle state of an automated verification run."""
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class RequirementVerdictStatus(str, Enum):
    """Truthful requirement-level verification outcome."""
    VERIFIED = "verified"
    FAILED = "failed"
    UNVERIFIED = "unverified"


class ArtifactMetadata(BaseModel):
    """Metadata for an ingested source or test code artifact."""
    id: str = Field(description="Stable artifact ID, e.g. ART-001")
    project_id: str
    relative_path: str
    file_type: FileType
    language: str
    sha256: str
    size_bytes: int
    line_count: int
    symbols: List[str] = Field(default_factory=list, description="Extracted functions and classes")
    created_at: str


class ProjectIngestionReport(BaseModel):
    """Report detailing uploaded and sanitized project archive."""
    project_id: str
    name: str
    total_files: int
    total_size_bytes: int
    detected_manifests: List[str] = Field(default_factory=list)
    detected_test_frameworks: List[str] = Field(default_factory=list)
    available_test_commands: List[str] = Field(default_factory=list)
    ingested_artifacts: List[ArtifactMetadata] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    ingested_at: str


class TraceabilityLink(BaseModel):
    """Bidirectional link connecting a requirement to a code artifact or test."""
    id: str = Field(description="Stable link ID, e.g. LNK-001")
    project_id: str
    specification_id: str
    requirement_id: str
    artifact_path: str
    symbol_name: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    link_type: LinkType
    link_origin: LinkOrigin
    confidence: float = Field(ge=0.0, le=1.0)
    is_confirmed: bool = False
    rationale: str
    created_at: str
    confirmed_at: Optional[str] = None


class RequirementEvidenceVerdict(BaseModel):
    """Requirement-level verification verdict based on actual test outcomes."""
    requirement_id: str
    requirement_title: str
    verdict: RequirementVerdictStatus
    linked_code_count: int
    linked_test_count: int
    passed_tests: List[str] = Field(default_factory=list)
    failed_tests: List[str] = Field(default_factory=list)
    rationale: str


class VerificationRun(BaseModel):
    """Record of an isolated Docker verification execution."""
    id: str = Field(description="Stable execution run ID, e.g. RUN-001")
    project_id: str
    specification_id: Optional[str] = None
    status: ExecutionStatus
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    duration_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    static_analysis_passed: bool = True
    static_findings: List[str] = Field(default_factory=list)
    requirement_verdicts: Dict[str, RequirementEvidenceVerdict] = Field(default_factory=dict)
    docker_available: bool = False
    created_at: str
    completed_at: Optional[str] = None


class RequirementEvidenceReport(BaseModel):
    """Aggregate requirement verification evidence and updated truthful coverage."""
    specification_id: str
    project_id: Optional[str] = None
    total_requirements: int
    candidate_code_linked_count: int
    confirmed_code_linked_count: int
    linked_test_count: int
    verified_requirement_count: int
    failed_requirement_count: int
    unverified_requirement_count: int
    verification_coverage_pct: float = Field(
        description="Percentage of requirements backed by passed test execution",
    )
    verdicts: List[RequirementEvidenceVerdict] = Field(default_factory=list)
    latest_run_id: Optional[str] = None
    latest_run_status: Optional[ExecutionStatus] = None
    notes: List[str] = Field(default_factory=list)


# -------------------------------------------------------------------------
# Request / Response Payloads
# -------------------------------------------------------------------------

class LinkRequirementsRequest(BaseModel):
    """Payload to trigger requirement linking against a project."""
    specification_id: str = Field(description="Target Phase 3 specification UUID")


class ConfirmLinkRequest(BaseModel):
    """Payload to confirm or reject a candidate traceability link."""
    is_confirmed: bool = Field(description="True to confirm link, False to set as candidate/rejected")


class TriggerRunRequest(BaseModel):
    """Payload to request an automated verification run."""
    specification_id: Optional[str] = None
    test_command: Optional[List[str]] = None


class ProjectSummary(BaseModel):
    """Summary of ingested project for listings."""
    project_id: str
    name: str
    total_files: int
    ingested_at: str
