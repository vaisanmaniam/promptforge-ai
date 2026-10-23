from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TaskCategory(str, Enum):
    """Software-development prompt task categories."""
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    CODE_REVIEW = "code_review"
    API_DEVELOPMENT = "api_development"
    SQL_GENERATION = "sql_generation"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    DEVOPS = "devops"


class ComponentType(str, Enum):
    """Prompt information components for software engineering requests."""
    OBJECTIVE = "objective"
    CONTEXT = "context"
    TARGET_TECHNOLOGY = "target_technology"
    INPUTS = "inputs"
    EXPECTED_OUTPUTS = "expected_outputs"
    FUNCTIONAL_REQUIREMENTS = "functional_requirements"
    CONSTRAINTS = "constraints"
    SECURITY_REQUIREMENTS = "security_requirements"
    TESTING_REQUIREMENTS = "testing_requirements"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"


class QualityAnnotation(BaseModel):
    """Ground-truth or reference quality sub-scores (0-100)."""
    clarity: float = Field(ge=0.0, le=100.0)
    context: float = Field(ge=0.0, le=100.0)
    specificity: float = Field(ge=0.0, le=100.0)
    constraints: float = Field(ge=0.0, le=100.0)
    output_definition: float = Field(ge=0.0, le=100.0)
    completeness: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)


class ExampleMetadata(BaseModel):
    """Provenance and split metadata for dataset governance."""
    source: str = Field(description="'curated_seed', 'synthetic', or 'reviewed_human'")
    split: str = Field(pattern="^(train|val|test)$", description="Dataset split assignment")
    is_synthetic: bool = Field(default=False, description="Flag identifying synthetic data generation")
    group_id: str = Field(description="Group or cluster ID to prevent train/test leakage")
    created_at: str = Field(description="ISO 8601 date string")


class PromptDatasetExample(BaseModel):
    """Schema-validated training/evaluation record for PromptForge AI."""
    example_id: str = Field(description="Unique stable identifier, e.g. 'PFE-0001'")
    prompt: str = Field(min_length=5, description="Full text of the prompt")
    task_category: TaskCategory = Field(description="Ground-truth category")
    components_present: List[ComponentType] = Field(default_factory=list)
    missing_information: List[ComponentType] = Field(default_factory=list)
    ambiguity_labels: List[str] = Field(default_factory=list)
    reference_quality: QualityAnnotation
    metadata: ExampleMetadata
