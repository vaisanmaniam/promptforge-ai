"""
Requirement Intelligence and Traceability Engine Schemas.
Defines strongly typed data structures for software requirements, validation rules,
directed traceability graphs, impact analysis, and verification coverage.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    """Core categories of software requirements."""
    FUNCTIONAL = "functional"
    NONFUNCTIONAL = "nonfunctional"
    TECHNICAL_CONSTRAINT = "technical_constraint"
    SECURITY = "security"


class RequirementPriority(str, Enum):
    """Risk and prioritization ranking."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RequirementStatus(str, Enum):
    """Delineation of explicit user requirements versus inferred system assumptions."""
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class VerificationState(str, Enum):
    """Life-cycle verification state of requirements."""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"


class VerificationType(str, Enum):
    """Method utilized or expected for verifying requirement satisfaction."""
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    STATIC_ANALYSIS = "static_analysis"
    MANUAL_REVIEW = "manual_review"


class AssumptionStatus(str, Enum):
    """Resolution status of an unconfirmed technical assumption."""
    UNRESOLVED = "unresolved"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class AcceptanceCriterion(BaseModel):
    """Formal, testable criterion for requirement satisfaction."""
    id: str = Field(description="Unique criterion ID, e.g. AC-001")
    description: str = Field(description="Verifiable condition or expected behavior")
    verification_type: VerificationType = Field(
        default=VerificationType.UNIT_TEST,
        description="Target verification strategy",
    )
    status: str = Field(default="pending", description="Verification status: pending, passed, failed")


class AssumptionItem(BaseModel):
    """An explicit or inferred assumption that requires engineer confirmation."""
    id: str = Field(description="Unique assumption ID, e.g. ASM-001")
    text: str = Field(description="Assumption description")
    source_component: str = Field(description="Originating component or context")
    status: AssumptionStatus = Field(default=AssumptionStatus.UNRESOLVED)
    impact: str = Field(
        default="medium",
        description="Potential architectural impact if assumption proves invalid: low, medium, high",
    )


class RequirementItem(BaseModel):
    """Structured, verifiable software engineering requirement."""
    id: str = Field(description="Stable identifier, e.g. REQ-001")
    title: str = Field(description="Concise requirement title")
    description: str = Field(description="Detailed requirement description")
    category: RequirementCategory = Field(description="Requirement classification")
    priority: RequirementPriority = Field(default=RequirementPriority.MEDIUM)
    status: RequirementStatus = Field(
        default=RequirementStatus.EXPLICIT,
        description="Explicitly provided by user or inferred by engine",
    )
    source_text: Optional[str] = Field(
        default=None,
        description="Source prompt sentence or component that originated this requirement",
    )
    assumptions: List[AssumptionItem] = Field(
        default_factory=list,
        description="Underlying assumptions tied to this requirement",
    )
    acceptance_criteria: List[AcceptanceCriterion] = Field(
        default_factory=list,
        description="Acceptance criteria required to verify this requirement",
    )
    verification_state: VerificationState = Field(
        default=VerificationState.UNVERIFIED,
        description="Current verification state",
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="List of requirement IDs that this requirement depends upon",
    )
    refines: List[str] = Field(
        default_factory=list,
        description="List of broader requirement IDs refined or specialized by this item",
    )


class RequirementSpecification(BaseModel):
    """Complete requirement specification containing all extracted items and global assumptions."""
    id: str = Field(description="Unique specification UUID")
    title: str = Field(description="Specification title")
    source_prompt: str = Field(description="Original user prompt")
    task_category: Optional[str] = Field(default=None, description="Classified software task category")
    category_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of requirements by category",
    )
    requirements: List[RequirementItem] = Field(default_factory=list)
    assumptions: List[AssumptionItem] = Field(
        default_factory=list,
        description="Global specification assumptions",
    )
    created_at: str = Field(description="ISO timestamp of creation")
    updated_at: str = Field(description="ISO timestamp of last update")
    version: int = Field(default=1, description="Specification revision number")


# -------------------------------------------------------------------------
# Validation Models
# -------------------------------------------------------------------------

class ValidationFinding(BaseModel):
    """Individual requirement validation issue or warning."""
    rule_id: str = Field(description="Unique rule code, e.g. VAGUE_QUALIFIER, MISSING_AC")
    severity: str = Field(pattern="^(error|warning|info)$", description="Finding severity")
    target_req_id: Optional[str] = Field(default=None, description="Target requirement ID if applicable")
    message: str = Field(description="Explanation of the issue found")
    suggestion: str = Field(description="Actionable remediation guidance")


class ValidationReport(BaseModel):
    """Aggregate validation findings for a requirement specification."""
    total_findings: int = 0
    errors: int = 0
    warnings: int = 0
    info: int = 0
    findings: List[ValidationFinding] = Field(default_factory=list)
    is_valid: bool = True


# -------------------------------------------------------------------------
# Traceability Graph Models
# -------------------------------------------------------------------------

class TraceabilityNode(BaseModel):
    """Node in the NetworkX directed traceability graph."""
    id: str = Field(description="Node ID (e.g. PROMPT-ROOT, REQ-001, CODE-001, TEST-001)")
    type: str = Field(description="'prompt', 'requirement', 'code_artifact', or 'test_case'")
    label: str = Field(description="Human readable label")
    category: Optional[str] = Field(default=None, description="Category for styling")
    status: Optional[str] = Field(default=None, description="Explicit/inferred or verification state")
    priority: Optional[str] = Field(default=None, description="Priority level")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TraceabilityEdge(BaseModel):
    """Directed edge in the traceability graph."""
    source: str = Field(description="Origin node ID")
    target: str = Field(description="Destination node ID")
    relation: str = Field(
        description="Edge semantic: 'generates', 'depends_on', 'refines', 'conflicts_with', 'verifies'",
    )


class TraceabilityGraph(BaseModel):
    """Directed Graph payload representing the traceability model."""
    nodes: List[TraceabilityNode] = Field(default_factory=list)
    edges: List[TraceabilityEdge] = Field(default_factory=list)
    has_cycles: bool = Field(default=False, description="True if circular dependencies were detected")
    cycle_paths: List[List[str]] = Field(default_factory=list, description="Cycle node sequences if any")
    isolated_nodes: List[str] = Field(default_factory=list, description="Nodes with zero connections")


class ImpactAnalysisReport(BaseModel):
    """Blast-radius analysis for changes to a specific requirement."""
    target_req_id: str
    upstream_dependencies: List[str] = Field(
        default_factory=list,
        description="Requirements that the target requirement relies on",
    )
    downstream_dependents: List[str] = Field(
        default_factory=list,
        description="Requirements that rely on the target requirement and would be impacted by changes",
    )
    impact_depth: int = Field(default=0, description="Maximum traversal depth of downstream impacts")
    risk_level: str = Field(default="low", description="low, medium, high, critical")


# -------------------------------------------------------------------------
# Coverage Models
# -------------------------------------------------------------------------

class CoverageReport(BaseModel):
    """
    Truthful traceability coverage metrics.
    Note: Code and test metrics are truthfully reported as unlinked until Phase 4 execution.
    """
    total_requirements: int
    explicit_count: int
    inferred_count: int
    prompt_coverage_pct: float = Field(
        description="Percentage of requirements traced back to source prompt root",
    )
    acceptance_criteria_coverage_pct: float = Field(
        description="Percentage of requirements with at least 1 defined acceptance criterion",
    )
    assumption_resolution_pct: float = Field(
        description="Percentage of assumptions resolved/confirmed",
    )
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    priority_distribution: Dict[str, int] = Field(default_factory=dict)
    code_traceability_status: str = Field(
        default="pending_phase_4",
        description="Truthful status of code linking (implemented in Phase 4)",
    )
    test_traceability_status: str = Field(
        default="pending_phase_4",
        description="Truthful status of test verification (implemented in Phase 4)",
    )
    summary_notes: List[str] = Field(default_factory=list)


# -------------------------------------------------------------------------
# API Request / Response Payloads
# -------------------------------------------------------------------------

class ExtractRequirementsRequest(BaseModel):
    """Payload to extract requirements from an unoptimized or optimized prompt."""
    prompt: str = Field(
        min_length=5,
        max_length=15000,
        description="Source prompt for requirement extraction",
        examples=["Build a rate-limited REST API in FastAPI with Redis caching and JWT authentication."],
    )
    task_category: Optional[str] = Field(default=None, description="Optional task category override")


class ExtractRequirementsResponse(BaseModel):
    """Response containing extracted specification and initial validation."""
    specification: RequirementSpecification
    validation: ValidationReport
    coverage: CoverageReport


class CreateSpecificationRequest(BaseModel):
    """Payload to persist a new specification."""
    title: Optional[str] = Field(default=None, description="Optional title, generated if absent")
    prompt: str = Field(min_length=5, max_length=15000)
    task_category: Optional[str] = Field(default=None)


class SpecificationSummary(BaseModel):
    """Lightweight summary of a stored specification for listing."""
    id: str
    title: str
    task_category: Optional[str]
    total_requirements: int
    created_at: str
    updated_at: str
    version: int


class SpecificationListResponse(BaseModel):
    """List response for stored specifications."""
    specifications: List[SpecificationSummary]
    total: int
