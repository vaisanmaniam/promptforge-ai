"""
Coverage and Traceability Analysis Engine.
Computes truthful traceability completeness metrics without fabricating code
or execution metrics prior to their respective implementation phases.
"""

from typing import Dict, List
from app.schemas.requirement import (
    AssumptionStatus,
    CoverageReport,
    RequirementSpecification,
)


class CoverageAnalyzer:
    """
    Computes truthful requirement coverage and assumption resolution metrics.
    """

    def analyze(self, spec: RequirementSpecification) -> CoverageReport:
        total = len(spec.requirements)
        if total == 0:
            return CoverageReport(
                total_requirements=0,
                explicit_count=0,
                inferred_count=0,
                prompt_coverage_pct=0.0,
                acceptance_criteria_coverage_pct=0.0,
                assumption_resolution_pct=0.0,
                category_distribution={},
                priority_distribution={},
                code_traceability_status="pending_phase_4",
                test_traceability_status="pending_phase_4",
                summary_notes=["Specification contains zero extracted requirements."],
            )

        explicit_count = sum(1 for r in spec.requirements if r.status.value == "explicit")
        inferred_count = sum(1 for r in spec.requirements if r.status.value == "inferred")

        # Every extracted requirement is tied to the prompt root
        prompt_cov_pct = 100.0

        # Requirements with at least 1 testable acceptance criterion
        with_ac = sum(1 for r in spec.requirements if len(r.acceptance_criteria) > 0)
        ac_cov_pct = round((with_ac / total) * 100.0, 1)

        # Assumptions resolution rate
        all_asms = list(spec.assumptions)
        for r in spec.requirements:
            all_asms.extend(r.assumptions)

        total_asms = len(all_asms)
        resolved_asms = sum(
            1 for a in all_asms if a.status in (AssumptionStatus.CONFIRMED, AssumptionStatus.REJECTED)
        )
        asm_resolution_pct = (
            round((resolved_asms / total_asms) * 100.0, 1) if total_asms > 0 else 100.0
        )

        # Distributions
        category_dist: Dict[str, int] = {}
        priority_dist: Dict[str, int] = {}

        for r in spec.requirements:
            cat = r.category.value
            pri = r.priority.value
            category_dist[cat] = category_dist.get(cat, 0) + 1
            priority_dist[pri] = priority_dist.get(pri, 0) + 1

        summary_notes: List[str] = []
        if ac_cov_pct == 100.0:
            summary_notes.append("100% of requirements have defined acceptance criteria.")
        else:
            summary_notes.append(f"{total - with_ac} requirement(s) lack acceptance criteria.")

        if total_asms > 0 and asm_resolution_pct < 100.0:
            unresolved = total_asms - resolved_asms
            summary_notes.append(
                f"{unresolved} unconfirmed assumption(s) require developer review before implementation."
            )

        summary_notes.append(
            "Code and test artifact traceability is pending Phase 4 verification sandbox integration."
        )

        return CoverageReport(
            total_requirements=total,
            explicit_count=explicit_count,
            inferred_count=inferred_count,
            prompt_coverage_pct=prompt_cov_pct,
            acceptance_criteria_coverage_pct=ac_cov_pct,
            assumption_resolution_pct=asm_resolution_pct,
            category_distribution=category_dist,
            priority_distribution=priority_dist,
            code_traceability_status="pending_phase_4",
            test_traceability_status="pending_phase_4",
            summary_notes=summary_notes,
        )
