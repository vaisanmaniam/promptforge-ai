"""
Schemas for Predictive Regression Testing ML Pipeline.
Defines strongly typed feature representations, historical observation records,
and dataset summary metrics with strict provenance tracking.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RegressionFeatureVector(BaseModel):
    """
    Normalized numerical feature representation of a (change, test) pair.
    Designed for local CPU-friendly scikit-learn training and inference.
    """
    change_file_count: int = Field(default=1, description="Total number of modified/added files in the change")
    is_direct_test_change: int = Field(default=0, description="1 if the test file itself was directly modified, else 0")
    symbol_overlap_count: int = Field(default=0, description="Number of AST symbols shared or invoked between change and test")
    requirement_priority_weight: float = Field(default=0.5, ge=0.0, le=1.0, description="Priority of linked requirement (Critical=1.0, High=0.75, Medium=0.5, Low=0.25)")
    dependency_distance: int = Field(default=0, ge=0, description="Graph traversal distance from changed requirement to test requirement")
    blast_radius_depth: int = Field(default=0, ge=0, description="Downstream impact depth of affected requirements")
    is_confirmed_link: int = Field(default=0, description="1 if traceability link is confirmed, 0 if candidate/unlinked")
    historical_failure_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Observed historical failure rate, or 0.0 if unknown")
    has_historical_data: int = Field(default=0, description="1 if genuine execution history exists, 0 if missing")
    historical_duration_normalized: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized past execution duration, or 0.0")

    @classmethod
    def feature_names(cls) -> List[str]:
        """Returns ordered list of feature keys for model serialization."""
        return [
            "change_file_count",
            "is_direct_test_change",
            "symbol_overlap_count",
            "requirement_priority_weight",
            "dependency_distance",
            "blast_radius_depth",
            "is_confirmed_link",
            "historical_failure_rate",
            "has_historical_data",
            "historical_duration_normalized",
        ]

    def to_array(self) -> List[float]:
        """Converts feature vector to float list ordered by feature_names()."""
        return [
            float(self.change_file_count),
            float(self.is_direct_test_change),
            float(self.symbol_overlap_count),
            float(self.requirement_priority_weight),
            float(self.dependency_distance),
            float(self.blast_radius_depth),
            float(self.is_confirmed_link),
            float(self.historical_failure_rate),
            float(self.has_historical_data),
            float(self.historical_duration_normalized),
        ]


class TestExecutionObservation(BaseModel):
    """
    A single historical observation of a test outcome following a code change.
    Used for training and evaluating predictive regression models.
    """
    __test__ = False

    observation_id: str = Field(description="Unique observation ID, e.g. OBS-001")
    change_id: str = Field(description="Change or commit identifier")
    project_id: str = Field(description="Project ID the observation belongs to")
    test_id: str = Field(description="Test node identifier (e.g. tests/test_calc.py::test_add)")
    outcome: int = Field(description="1 if test detected a regression / failed, 0 if test passed")
    features: RegressionFeatureVector
    label_provenance: str = Field(description="Origin of label (e.g. 'docker_verification_run', 'synthetic_pipeline_test')")
    is_synthetic: bool = Field(default=False, description="True if artificially generated for pipeline unit tests")
    timestamp: str = Field(description="ISO-8601 timestamp of observation")


class DatasetSummary(BaseModel):
    """
    Statistical summary of a training or evaluation dataset.
    """
    total_samples: int
    positive_count: int = Field(description="Number of regression / failure samples (outcome=1)")
    negative_count: int = Field(description="Number of passing samples (outcome=0)")
    positive_ratio: float
    unique_changes: int
    unique_projects: int
    provenance_counts: Dict[str, int] = Field(default_factory=dict)
    has_synthetic: bool
    status: str = Field(default="valid", description="'valid', 'insufficient_data', 'single_class_detected'")
