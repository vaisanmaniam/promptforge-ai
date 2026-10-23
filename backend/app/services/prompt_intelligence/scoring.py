import re
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.services.prompt_intelligence.ambiguity import AmbiguityReport
from app.services.prompt_intelligence.components import ComponentDetectionReport

DEFAULT_WEIGHTS = {
    "clarity": 0.20,
    "context": 0.15,
    "specificity": 0.20,
    "constraints": 0.15,
    "output_definition": 0.15,
    "completeness": 0.15,
}


class DimensionScore(BaseModel):
    """Score breakdown for a single quality dimension."""
    dimension: str
    weight: float
    score: float = Field(ge=0.0, le=100.0)
    weighted_score: float
    explanation: str


class QualityAssessment(BaseModel):
    """Overall prompt quality evaluation with explainable breakdown."""
    overall_score: float = Field(ge=0.0, le=100.0, description="Weighted aggregate quality score [0-100]")
    dimension_scores: Dict[str, DimensionScore]
    positive_evidence: List[str]
    missing_information: List[str]
    recommendations: List[str]
    scoring_version: str = "v1.0.0-deterministic"
    method: str = "rule_based_deterministic"


class QualityScorer:
    """
    Deterministic prompt-quality scoring engine.
    Calculates weighted sub-scores across 6 software engineering dimensions.
    """

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_WEIGHTS
        total_weight = sum(self.weights.values())
        if not (0.999 <= total_weight <= 1.001):
            raise ValueError(f"Quality weights must sum to 1.0, got {total_weight}")

    def evaluate(
        self,
        prompt: str,
        comp_report: ComponentDetectionReport,
        amb_report: AmbiguityReport,
        task_category: str = "code_generation",
    ) -> QualityAssessment:
        text = prompt.strip()
        words = text.split()
        word_count = len(words)

        positive_evidence: List[str] = []
        missing_info: List[str] = []
        recommendations: List[str] = []

        # --- 1. CLARITY (Weight: 20%) ---
        clarity_score = 90.0
        clarity_notes = []
        if word_count < 10:
            clarity_score -= 40.0
            clarity_notes.append("Prompt is extremely terse (<10 words)")
        elif word_count < 20:
            clarity_score -= 20.0
            clarity_notes.append("Prompt is short (<20 words)")

        # Ambiguity penalty
        if amb_report.ambiguity_count > 0:
            pen = min(amb_report.ambiguity_count * 15.0, 45.0)
            clarity_score -= pen
            clarity_notes.append(f"Contains {amb_report.ambiguity_count} ambiguous qualifier(s)")

        # Formatting bonus
        if any(marker in text for marker in ["\n- ", "\n* ", "\n1. ", "```", "###"]):
            clarity_score += 10.0
            clarity_notes.append("Structured with markdown lists or code blocks")
            positive_evidence.append("Structured format improves readability and requirements isolation.")

        clarity_score = max(10.0, min(100.0, clarity_score))
        clarity_explanation = "; ".join(clarity_notes) if clarity_notes else "Direct and readable phrasing."

        # --- 2. CONTEXT (Weight: 15%) ---
        context_score = 30.0
        context_notes = []
        if "context" in comp_report.detected:
            context_score += 45.0
            context_notes.append("Provides architecture or background domain context")
            positive_evidence.append("Includes background context explaining operational environment.")
        elif "context" in comp_report.uncertain:
            context_score += 20.0
            context_notes.append("Partial context present")
        else:
            missing_info.append("Operational background or application architecture context is absent.")
            recommendations.append("Add context: Explain where and how this component fits into the broader architecture.")

        if re.search(r"\b(production|legacy|existing|system|service|database|schema)\b", text, re.I):
            context_score += 25.0
            context_notes.append("Specifies target system context")

        context_score = max(10.0, min(100.0, context_score))
        context_explanation = "; ".join(context_notes) if context_notes else "Limited context regarding existing system."

        # --- 3. SPECIFICITY (Weight: 20%) ---
        spec_score = 30.0
        spec_notes = []
        if "target_technology" in comp_report.detected:
            spec_score += 40.0
            spec_notes.append("Explicitly states target technology/framework")
            positive_evidence.append("Clearly defines target language, framework, or runtime environment.")
        else:
            missing_info.append("Target technology (language, library, runtime) is not specified.")
            recommendations.append("Specify technology: Explicitly name the language, framework, and required library versions.")

        if "inputs" in comp_report.detected:
            spec_score += 30.0
            spec_notes.append("Explicitly defines inputs/parameters")
            positive_evidence.append("Defines input arguments, data structures, or parameters.")
        else:
            recommendations.append("Define inputs: Specify argument names, data types, and expected payload formats.")

        spec_score = max(10.0, min(100.0, spec_score))
        spec_explanation = "; ".join(spec_notes) if spec_notes else "General request without technical specificity."

        # --- 4. CONSTRAINTS (Weight: 15%) ---
        const_score = 25.0
        const_notes = []
        if "constraints" in comp_report.detected:
            const_score += 45.0
            const_notes.append("Specifies explicit complexity, resource, or operational constraints")
            positive_evidence.append("States concrete boundaries (complexity, memory, or timeouts).")
        else:
            recommendations.append("Add constraints: Define performance budgets (latency SLA), memory caps, or error boundaries.")

        if re.search(r"\b(error|exception|raise|throw|status\s+code|catch|fail)\b", text, re.I):
            const_score += 30.0
            const_notes.append("Specifies error handling requirements")
            positive_evidence.append("Specifies explicit error conditions and exception handling.")

        const_score = max(10.0, min(100.0, const_score))
        const_explanation = "; ".join(const_notes) if const_notes else "Few or no engineering constraints specified."

        # --- 5. OUTPUT DEFINITION (Weight: 15%) ---
        out_score = 25.0
        out_notes = []
        if "expected_outputs" in comp_report.detected:
            out_score += 50.0
            out_notes.append("Explicitly specifies return types, format, or HTTP status codes")
            positive_evidence.append("Defines expected output schema, return types, or status codes.")
        else:
            missing_info.append("Expected output schema or return value structure is not specified.")
            recommendations.append("Define outputs: Clarify the exact return structure, schema, or HTTP response.")

        if re.search(r"\b(json|schema|format|status|dict|array|http|xml)\b", text, re.I):
            out_score += 25.0
            out_notes.append("Includes serialization or schema output format")

        out_score = max(10.0, min(100.0, out_score))
        out_explanation = "; ".join(out_notes) if out_notes else "Unspecified return shape or success criteria."

        # --- 6. COMPLETENESS (Weight: 15%) ---
        # Core expected dimensions for software requests
        core_expected = ["objective", "target_technology", "inputs", "expected_outputs", "functional_requirements", "constraints"]
        detected_core = [c for c in core_expected if c in comp_report.detected]
        comp_ratio = len(detected_core) / float(len(core_expected))
        comp_score = max(15.0, min(100.0, comp_ratio * 100.0))
        comp_explanation = f"Detected {len(detected_core)} of {len(core_expected)} core engineering components."

        dimension_scores = {
            "clarity": DimensionScore(
                dimension="clarity",
                weight=self.weights["clarity"],
                score=round(clarity_score, 1),
                weighted_score=round(clarity_score * self.weights["clarity"], 2),
                explanation=clarity_explanation,
            ),
            "context": DimensionScore(
                dimension="context",
                weight=self.weights["context"],
                score=round(context_score, 1),
                weighted_score=round(context_score * self.weights["context"], 2),
                explanation=context_explanation,
            ),
            "specificity": DimensionScore(
                dimension="specificity",
                weight=self.weights["specificity"],
                score=round(spec_score, 1),
                weighted_score=round(spec_score * self.weights["specificity"], 2),
                explanation=spec_explanation,
            ),
            "constraints": DimensionScore(
                dimension="constraints",
                weight=self.weights["constraints"],
                score=round(const_score, 1),
                weighted_score=round(const_score * self.weights["constraints"], 2),
                explanation=const_explanation,
            ),
            "output_definition": DimensionScore(
                dimension="output_definition",
                weight=self.weights["output_definition"],
                score=round(out_score, 1),
                weighted_score=round(out_score * self.weights["output_definition"], 2),
                explanation=out_explanation,
            ),
            "completeness": DimensionScore(
                dimension="completeness",
                weight=self.weights["completeness"],
                score=round(comp_score, 1),
                weighted_score=round(comp_score * self.weights["completeness"], 2),
                explanation=comp_explanation,
            ),
        }

        overall = sum(ds.weighted_score for ds in dimension_scores.values())

        return QualityAssessment(
            overall_score=round(overall, 1),
            dimension_scores=dimension_scores,
            positive_evidence=positive_evidence,
            missing_information=missing_info,
            recommendations=recommendations[:4],
            scoring_version="v1.0.0-deterministic",
            method="rule_based_deterministic",
        )
