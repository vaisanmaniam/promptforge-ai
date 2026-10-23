"""
Pydantic schemas for Predictive Regression Testing Engine.
Defines strongly typed payloads for change impact analysis, deterministic prioritization,
predictive ML test selection, historical observation tracking, and model lifecycle telemetry.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Type of file alteration detected or specified."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


class PrioritizationStrategy(str, Enum):
    """Test ranking and selection strategy."""
    ALL_TESTS = "all_tests"
    IMPACT_BASED = "impact_based"
    PREDICTIVE = "predictive"


class ChangedFileInfo(BaseModel):
    """Detailed metadata for an individual modified file."""
    file_path: str
    change_type: ChangeType
    changed_symbols: List[str] = Field(default_factory=list, description="Extracted modified classes and functions")
    is_test: bool = False


class AffectedRequirementInfo(BaseModel):
    """Requirement identified as affected by change impact propagation."""
    requirement_id: str
    title: str
    priority: str
    is_directly_changed: bool
    impact_distance: int = Field(ge=0, description="0 for direct link, 1+ for downstream dependent")
    linked_code_artifacts: List[str] = Field(default_factory=list)


class ChangeImpactReport(BaseModel):
    """Structured report detailing the scope and blast radius of a code change."""
    analysis_id: str = Field(description="Stable analysis ID, e.g. ANL-001")
    project_id: str
    changed_files: List[ChangedFileInfo] = Field(default_factory=list)
    changed_symbols: List[str] = Field(default_factory=list)
    directly_affected_requirements: List[AffectedRequirementInfo] = Field(default_factory=list)
    downstream_affected_requirements: List[AffectedRequirementInfo] = Field(default_factory=list)
    max_blast_radius_depth: int = 0
    affected_tests_candidate_count: int = 0
    evidence_disclosures: List[str] = Field(default_factory=list)
    created_at: str


class RankedTestItem(BaseModel):
    """Prioritized test item with regression risk score and human-readable rationale."""
    rank: int
    test_id: str = Field(description="Unique pytest node id, e.g. tests/test_calc.py::test_add")
    file_path: str
    symbol_name: Optional[str] = None
    score: float = Field(ge=0.0, le=1.0, description="Normalized regression risk score")
    predicted_failure_probability: Optional[float] = Field(default=None, description="ML predicted probability if trained")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    explanations: List[str] = Field(default_factory=list)
    is_directly_affected: bool = False
    verifies_requirement_id: Optional[str] = None
    historical_failure_rate: Optional[float] = None
    historical_duration_ms: Optional[float] = None
    method: str = Field(default="deterministic_baseline")
    is_selected: bool = True


class ExcludedTestItem(BaseModel):
    """Test omitted from final selection with explicit rationale."""
    test_id: str
    rank: int
    score: float
    exclusion_reason: str


class PrioritizationReport(BaseModel):
    """Report containing full ranking of all discovered tests for a given change."""
    analysis_id: str
    project_id: str
    strategy_used: PrioritizationStrategy
    fallback_to_baseline: bool = False
    fallback_reason: Optional[str] = None
    model_status: str
    total_tests_discovered: int
    ranked_tests: List[RankedTestItem] = Field(default_factory=list)
    created_at: str


class TestSelectionReport(BaseModel):
    """Selection report separating tests to run from excluded tests with explicit rationale."""
    analysis_id: str
    project_id: str
    strategy: PrioritizationStrategy
    total_tests: int
    selected_count: int
    excluded_count: int
    selected_tests: List[RankedTestItem] = Field(default_factory=list)
    excluded_tests: List[ExcludedTestItem] = Field(default_factory=list)
    estimated_duration_ms: float = 0.0
    fallback_to_baseline: bool = False
    fallback_reason: Optional[str] = None
    created_at: str


class ModelStatusReport(BaseModel):
    """Operational telemetry for the predictive ML model."""
    model_name: str
    status: str = Field(description="'trained' or 'not_trained'")
    is_trained: bool
    version: str
    resolved_path: str
    training_sample_count: int = 0
    fallback_behavior: str
    notes: str
    evaluation_metrics: Dict[str, Any] = Field(default_factory=dict)


class HistoricalObservationSummary(BaseModel):
    """Summary of historical test execution data collected from verification runs."""
    total_observations: int
    unique_tests: int
    unique_changes: int
    passed_count: int
    failed_count: int
    has_genuine_failures: bool
    provenance_distribution: Dict[str, int] = Field(default_factory=dict)


# -------------------------------------------------------------------------
# Request Payloads
# -------------------------------------------------------------------------

class ChangeImpactRequest(BaseModel):
    """Payload to request change impact analysis for a project."""
    project_id: str
    changed_files: List[str] = Field(default_factory=list, description="Relative paths of changed files")
    file_contents: Optional[Dict[str, str]] = Field(default=None, description="Optional updated file contents for AST diffing")
    diff_text: Optional[str] = Field(default=None, description="Optional unified diff text")


class PrioritizationRequest(BaseModel):
    """Payload to trigger test prioritization for a change."""
    project_id: str
    changed_files: List[str] = Field(default_factory=list)
    file_contents: Optional[Dict[str, str]] = None
    strategy: PrioritizationStrategy = PrioritizationStrategy.PREDICTIVE
    top_k: Optional[int] = None
    execution_budget_ms: Optional[float] = None


class TestSelectionRequest(BaseModel):
    """Payload to select tests under a specific budget or top-k."""
    project_id: str
    changed_files: List[str] = Field(default_factory=list)
    file_contents: Optional[Dict[str, str]] = None
    strategy: PrioritizationStrategy = PrioritizationStrategy.PREDICTIVE
    top_k: Optional[int] = None
    execution_budget_ms: Optional[float] = None


class ModelTrainingRequest(BaseModel):
    """Payload to trigger model training on available observations."""
    include_synthetic: bool = Field(default=False, description="If True, includes synthetic samples for pipeline verification")
    algorithm: str = Field(default="RandomForestClassifier")


class ModelEvaluationRequest(BaseModel):
    """Payload to trigger model evaluation."""
    include_synthetic: bool = Field(default=False)
    top_k: int = 3


class ModelTrainingReport(BaseModel):
    """Report generated following model training."""
    success: bool
    status: str
    message: str
    dataset_summary: Dict[str, Any] = Field(default_factory=dict)
    evaluation_metrics: Dict[str, Any] = Field(default_factory=dict)

