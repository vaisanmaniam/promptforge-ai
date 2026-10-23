from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.services.prompt_intelligence.ambiguity import AmbiguityReport
from app.services.prompt_intelligence.components import ComponentDetectionReport


class PromptOptimizationResult(BaseModel):
    """Result of deterministic prompt enhancement."""
    original_prompt: str
    optimized_prompt: str
    task_category: str
    added_sections: List[str]
    assumptions: List[str]
    clarification_questions: List[str]
    explanation_of_changes: List[str]


CATEGORY_TEMPLATES = {
    "code_generation": {
        "sections": ["Technical Context", "Functional Specifications", "Input & Output Schema", "Constraints & Error Handling", "Acceptance Criteria"],
        "default_tech": "Python 3.11 (standard library or modern type annotations)",
    },
    "debugging": {
        "sections": ["Observed Problem & Error Trace", "Environment & Runtime Context", "Reproduction Steps", "Target Correct Behavior", "Constraints"],
        "default_tech": "Target language and runtime where the error occurred",
    },
    "api_development": {
        "sections": ["HTTP Specification", "Request & Response Schema", "Authentication & Authorization", "Validation & Error Responses", "Constraints & Security"],
        "default_tech": "FastAPI (Python 3.11) with Pydantic v2 validation",
    },
    "sql_generation": {
        "sections": ["Database Schema & Dialect", "Query Goal & Business Logic", "Expected Result Format", "Performance & Index Constraints"],
        "default_tech": "PostgreSQL 16 syntax",
    },
    "code_review": {
        "sections": ["Target Code & Context", "Review Focus Areas (Security, Performance, SOLID)", "Evaluation Criteria"],
        "default_tech": "Target codebase language and framework",
    },
    "test_generation": {
        "sections": ["Target Component Under Test", "Test Scope & Types (Unit, Integration, Edge Cases)", "Mocking & Fixtures Strategy", "Acceptance Assertions"],
        "default_tech": "pytest (Python) or Jest (JavaScript/TypeScript)",
    },
    "documentation": {
        "sections": ["Target Audience & Scope", "Documentation Structure", "Code & Schema Examples", "Style Guide Standards"],
        "default_tech": "Markdown specification with OpenAPI / code examples",
    },
    "devops": {
        "sections": ["Infrastructure Target", "Configuration Requirements", "Security & Resource Limits", "Deployment Verification"],
        "default_tech": "Docker (Linux container) / GitHub Actions / Kubernetes",
    },
}


class PromptOptimizer:
    """
    Deterministic rule-based prompt optimization engine.
    Restructures requests into verifiable software engineering prompts without hallucinating facts.
    """

    def optimize(
        self,
        prompt: str,
        task_category: str,
        comp_report: ComponentDetectionReport,
        amb_report: AmbiguityReport,
    ) -> PromptOptimizationResult:
        original = prompt.strip()
        cat = task_category if task_category in CATEGORY_TEMPLATES else "code_generation"
        template_info = CATEGORY_TEMPLATES[cat]

        added_sections: List[str] = []
        assumptions: List[str] = []
        clarification_questions: List[str] = []
        explanations: List[str] = [
            "Preserved original request verbatim as the core objective.",
            "Restructured unstructured text into standardized software engineering sections.",
        ]

        # Gather clarifications from detected ambiguities
        for finding in amb_report.findings:
            clarification_questions.append(
                f"Clarify '{finding.term}': {finding.clarification_question}"
            )

        # Check for technology assumption
        tech_specified = "target_technology" in comp_report.detected
        if not tech_specified:
            assumed_tech = template_info["default_tech"]
            assumptions.append(
                f"Target Technology: Proposed {assumed_tech} because no specific language/framework was stated."
            )
            clarification_questions.append(
                f"Confirm Technology: Is {assumed_tech} acceptable, or do you require a different stack?"
            )
            explanations.append(f"Exposed proposed technology assumption ({assumed_tech}) for user confirmation.")

        # Build structured prompt
        lines: List[str] = []
        lines.append(f"### 1. Objective")
        lines.append(original)
        lines.append("")

        lines.append(f"### 2. Technical Context & Stack")
        if tech_specified:
            lines.append("- Technology explicitly defined in prompt.")
        else:
            lines.append(f"- [PROPOSED ASSUMPTION - Requires Confirmation]: {template_info['default_tech']}")
        added_sections.append("Technical Context & Stack")
        lines.append("")

        lines.append(f"### 3. Functional Requirements & Specifications")
        lines.append("- Implement complete, modular, and maintainable logic directly addressing the objective.")
        lines.append("- Structure functions with clear responsibilities and explicit type annotations.")
        added_sections.append("Functional Requirements & Specifications")
        lines.append("")

        # Category-specific sections
        if cat in ("code_generation", "api_development"):
            lines.append("### 4. Input & Output Contract")
            if "inputs" in comp_report.detected:
                lines.append("- Inputs: Process arguments as specified in the original request.")
            else:
                lines.append("- [PROPOSED ASSUMPTION]: Validate all inputs, rejecting malformed types with descriptive exceptions.")
                assumptions.append("Input Validation: Assumed strict parameter validation.")
            if "expected_outputs" in comp_report.detected:
                lines.append("- Outputs: Return formatted response conforming to requested output type.")
            else:
                lines.append("- [PROPOSED ASSUMPTION]: Return deterministic, schema-validated outputs.")
            added_sections.append("Input & Output Contract")
            lines.append("")

        elif cat == "sql_generation":
            lines.append("### 4. Schema & Dialect Details")
            lines.append("- Ensure query conforms to PostgreSQL 16 standard dialect.")
            lines.append("- Use appropriate index-friendly filtering and explicit JOIN conditions.")
            added_sections.append("Schema & Dialect Details")
            lines.append("")

        elif cat == "debugging":
            lines.append("### 4. Root Cause Analysis & Fix Strategy")
            lines.append("- Identify the exact line or condition triggering the failure.")
            lines.append("- Provide minimal, targeted patch preserving surrounding behavior.")
            added_sections.append("Root Cause Analysis & Fix Strategy")
            lines.append("")

        lines.append(f"### 5. Constraints & Edge Cases")
        lines.append("- Handle null, empty, boundary, and unexpected values gracefully.")
        lines.append("- Do not use insecure evaluation methods or hardcode secrets.")
        added_sections.append("Constraints & Edge Cases")
        lines.append("")

        lines.append(f"### 6. Verification Criteria")
        lines.append("- Provide reproducible test cases validating happy paths and boundary conditions.")
        lines.append("- Code must pass automated static analysis without unhandled exceptions.")
        added_sections.append("Verification Criteria")

        optimized_text = "\n".join(lines)

        return PromptOptimizationResult(
            original_prompt=original,
            optimized_prompt=optimized_text,
            task_category=cat,
            added_sections=added_sections,
            assumptions=assumptions,
            clarification_questions=clarification_questions,
            explanation_of_changes=explanations,
        )
