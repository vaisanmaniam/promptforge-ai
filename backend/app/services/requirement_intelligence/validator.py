"""
Requirement Validator.
Performs semantic and structural analysis on requirement specifications:
detects vague qualifiers, missing acceptance criteria, unresolved assumptions,
and architectural contradictions.
"""

import re
from typing import List, Tuple
from app.schemas.requirement import (
    AssumptionStatus,
    RequirementSpecification,
    ValidationFinding,
    ValidationReport,
)

VAGUE_TERMS = [
    r"\bfast\b",
    r"\bscalable\b",
    r"\buser[- ]friendly\b",
    r"\brobust\b",
    r"\beasy\b",
    r"\betc\.?\b",
    r"\band\s+so\s+on\b",
    r"\bflexible\b",
    r"\boptimal\b",
    r"\bhigh[- ]performance\b",
]

QUANTITATIVE_INDICATORS = [
    r"\b\d+\s*(ms|s|seconds|minutes|mb|gb|kb|qps|rps|req/s|%)\b",
    r"\bo\([1n]|log\s*n\)",
    r"\b(http\s+status|200|201|400|401|403|404|500)\b",
    r"\b\d+\s*(users|connections|threads|workers)\b",
]


class RequirementValidator:
    """
    Validates requirement specifications against rigorous software engineering standards.
    """

    def validate(self, spec: RequirementSpecification) -> ValidationReport:
        findings: List[ValidationFinding] = []

        # 1. Rule: Missing Acceptance Criteria
        for req in spec.requirements:
            if not req.acceptance_criteria:
                findings.append(
                    ValidationFinding(
                        rule_id="MISSING_ACCEPTANCE_CRITERIA",
                        severity="error",
                        target_req_id=req.id,
                        message=f"Requirement {req.id} ('{req.title}') has no testable acceptance criteria.",
                        suggestion="Define at least one automated unit test, integration test, or static assertion.",
                    )
                )

        # 2. Rule: Vague Qualifiers
        for req in spec.requirements:
            combined_text = f"{req.title} {req.description} " + " ".join(
                ac.description for ac in req.acceptance_criteria
            )
            vague_matches = []
            for pattern in VAGUE_TERMS:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    vague_matches.append(match.group(0))

            has_quant = any(
                re.search(q, combined_text, re.IGNORECASE) for q in QUANTITATIVE_INDICATORS
            )

            if vague_matches and not has_quant:
                terms_str = ", ".join(f"'{m}'" for m in set(vague_matches))
                findings.append(
                    ValidationFinding(
                        rule_id="VAGUE_QUALIFIER",
                        severity="warning",
                        target_req_id=req.id,
                        message=f"Requirement {req.id} contains vague qualifier(s) {terms_str} without measurable thresholds.",
                        suggestion="Specify bounded metrics (e.g. latency in milliseconds, concurrency limits, or complexity bounds).",
                    )
                )

        # 3. Rule: Unresolved Assumptions
        all_assumptions = list(spec.assumptions)
        for req in spec.requirements:
            all_assumptions.extend(req.assumptions)

        unresolved_asms = [a for a in all_assumptions if a.status == AssumptionStatus.UNRESOLVED]
        if unresolved_asms:
            for asm in unresolved_asms:
                findings.append(
                    ValidationFinding(
                        rule_id="UNRESOLVED_ASSUMPTION",
                        severity="warning" if asm.impact == "high" else "info",
                        target_req_id=None,
                        message=f"Unresolved assumption '{asm.text}' ({asm.id}) may lead to implementation divergence.",
                        suggestion=f"Confirm, adjust, or reject this assumption in specification configuration (Impact: {asm.impact}).",
                    )
                )

        # 4. Rule: Direct Dependency Cycle / Self Dependency
        for req in spec.requirements:
            if req.id in req.depends_on:
                findings.append(
                    ValidationFinding(
                        rule_id="SELF_DEPENDENCY",
                        severity="error",
                        target_req_id=req.id,
                        message=f"Requirement {req.id} lists itself as a dependency.",
                        suggestion="Remove self-referencing dependency link.",
                    )
                )

        # 5. Rule: Architectural Contradictions
        contradiction_findings = self._detect_contradictions(spec)
        findings.extend(contradiction_findings)

        errors_count = sum(1 for f in findings if f.severity == "error")
        warnings_count = sum(1 for f in findings if f.severity == "warning")
        info_count = sum(1 for f in findings if f.severity == "info")

        return ValidationReport(
            total_findings=len(findings),
            errors=errors_count,
            warnings=warnings_count,
            info=info_count,
            findings=findings,
            is_valid=(errors_count == 0),
        )

    def _detect_contradictions(self, spec: RequirementSpecification) -> List[ValidationFinding]:
        findings: List[ValidationFinding] = []
        full_spec_text = (
            spec.source_prompt
            + " "
            + " ".join(f"{r.title} {r.description}" for r in spec.requirements)
        ).lower()

        # Rule A: Stateless REST vs In-Memory Session Storage
        if "stateless" in full_spec_text and ("session" in full_spec_text or "in-memory state" in full_spec_text):
            if not ("jwt" in full_spec_text or "token" in full_spec_text or "redis" in full_spec_text):
                findings.append(
                    ValidationFinding(
                        rule_id="ARCHITECTURAL_CONTRADICTION",
                        severity="warning",
                        target_req_id=None,
                        message="Potential contradiction: specification mentions 'stateless' architecture alongside session/state retention.",
                        suggestion="Clarify session management mechanism (e.g. self-contained JWT or external distributed store like Redis).",
                    )
                )

        # Rule B: Standard Library Only vs External Package Requirement
        no_external = any(
            phrase in full_spec_text
            for phrase in ["no external libraries", "standard library only", "without third-party", "pure standard library"]
        )
        has_external_pkg = any(
            pkg in full_spec_text
            for pkg in ["fastapi", "django", "flask", "redis", "celery", "pydantic", "sqlalchemy", "docker"]
        )
        if no_external and has_external_pkg:
            findings.append(
                ValidationFinding(
                    rule_id="CONSTRAINTS_CONFLICT",
                    severity="error",
                    target_req_id=None,
                    message="Conflict between 'standard library only' constraint and declared external dependencies.",
                    suggestion="Remove either the third-party framework dependency or the standard-library-only restriction.",
                )
            )

        return findings
