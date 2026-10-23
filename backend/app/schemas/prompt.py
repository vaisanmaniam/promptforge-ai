from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ai.prompt_classifier.base import ClassificationResult
from app.services.prompt_intelligence.ambiguity import AmbiguityReport
from app.services.prompt_intelligence.components import ComponentDetectionReport
from app.services.prompt_intelligence.optimizer import PromptOptimizationResult
from app.services.prompt_intelligence.scoring import QualityAssessment
from app.services.prompt_intelligence.tokenizer import TokenAnalysisReport


class AnalyzePromptRequest(BaseModel):
    """Payload for analyzing software development prompts."""
    prompt: str = Field(
        min_length=1,
        max_length=10000,
        description="Software development prompt to analyze",
        examples=["Implement a thread-safe LRU cache in Python with O(1) operations."],
    )
    task_category: Optional[str] = Field(
        default=None,
        description="Optional manual task category override",
    )


class AnalyzePromptResponse(BaseModel):
    """Complete diagnostic analysis response."""
    task_classification: ClassificationResult
    components: ComponentDetectionReport
    ambiguity: AmbiguityReport
    quality: QualityAssessment
    token_count: int
    token_counting_method: str
    tokenizer_identity: str
    is_exact_tokens: bool


class OptimizePromptRequest(BaseModel):
    """Payload for optimizing a software prompt."""
    prompt: str = Field(
        min_length=1,
        max_length=10000,
        description="Software prompt to optimize and structure",
        examples=["Create an API for user authentication with security."],
    )
    task_category: Optional[str] = Field(
        default=None,
        description="Optional manual task category override",
    )


class OptimizePromptResponse(BaseModel):
    """Optimization response including before-and-after evaluations and assumptions."""
    optimization: PromptOptimizationResult
    task_classification: ClassificationResult
    original_quality: QualityAssessment
    optimized_quality: QualityAssessment
    token_analysis: TokenAnalysisReport
