"""
Deterministic Prioritization Baseline Service.
Computes explainable, risk-weighted test rankings using structural code relationships,
Phase 3 requirement priorities, graph blast radius, and historical test reliability.
Operates deterministically without requiring a trained ML model.
"""

from typing import Dict, List, Optional, Set, Tuple
from app.schemas.regression import ChangeImpactReport, RankedTestItem
from app.schemas.requirement import RequirementPriority, RequirementSpecification
from app.schemas.verification import ArtifactMetadata, FileType, ProjectIngestionReport, TraceabilityLink
from app.services.regression.history import TestHistoryRepository


class DeterministicPrioritizer:
    """
    Ranks tests using an explainable multi-signal formula with human-readable rationale.
    """

    # Signal weights (sum to 1.0)
    WEIGHT_DIRECT_CODE = 0.35
    WEIGHT_REQUIREMENT = 0.25
    WEIGHT_PRIORITY = 0.15
    WEIGHT_BLAST_RADIUS = 0.15
    WEIGHT_HISTORY = 0.10

    PRIORITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.75,
        "medium": 0.50,
        "low": 0.25,
    }

    def __init__(self, history_repo: Optional[TestHistoryRepository] = None):
        self.history_repo = history_repo or TestHistoryRepository()

    def rank_tests(
        self,
        impact: ChangeImpactReport,
        project: ProjectIngestionReport,
        links: List[TraceabilityLink],
        spec: Optional[RequirementSpecification] = None,
        discovered_test_nodes: Optional[List[str]] = None,
    ) -> List[RankedTestItem]:
        """
        Ranks all discovered or cataloged tests based on the deterministic risk formula.
        Returns a sorted list of RankedTestItem objects (rank 1 = highest risk).
        """
        changed_paths = {c.file_path for c in impact.changed_files}
        changed_symbols = set(impact.changed_symbols)

        # Directly and downstream affected requirement IDs
        direct_req_ids = {r.requirement_id: r for r in impact.directly_affected_requirements}
        downstream_req_ids = {r.requirement_id: r for r in impact.downstream_affected_requirements}

        # Build candidate test items to rank
        # 1. From discovered_test_nodes (e.g. tests/test_calc.py::test_add)
        # 2. Or from project.ingested_artifacts where file_type == TEST_FILE
        test_candidates: List[Tuple[str, str, Optional[str]]] = []  # (test_id, file_path, symbol_name)

        if discovered_test_nodes:
            for t_node in discovered_test_nodes:
                parts = t_node.split("::")
                f_path = parts[0].replace("\\", "/")
                s_name = parts[1] if len(parts) > 1 else None
                test_candidates.append((t_node, f_path, s_name))
        else:
            for art in project.ingested_artifacts:
                if art.file_type == FileType.TEST_FILE:
                    art_path = art.relative_path.replace("\\", "/")
                    if art.symbols:
                        for sym in art.symbols:
                            s_clean = sym.split(":")[-1]
                            test_candidates.append((f"{art_path}::{s_clean}", art_path, s_clean))
                    else:
                        test_candidates.append((art_path, art_path, None))

        # Deduplicate
        seen_test_ids: Set[str] = set()
        unique_candidates = []
        for c in test_candidates:
            if c[0] not in seen_test_ids:
                seen_test_ids.add(c[0])
                unique_candidates.append(c)

        scored_items: List[RankedTestItem] = []

        for test_id, file_path, symbol_name in unique_candidates:
            explanations: List[str] = []
            score_components: float = 0.0

            # 1. Direct code change component (weight 0.35)
            f_direct = 0.0
            is_directly_affected = False

            if file_path in changed_paths:
                f_direct = 1.0
                is_directly_affected = True
                explanations.append(f"Test file '{file_path}' was directly modified in the change set.")
            elif symbol_name and any(cs.lower() in symbol_name.lower() for cs in changed_symbols):
                f_direct = 0.8
                is_directly_affected = True
                explanations.append(f"Test method '{symbol_name}' directly matches changed symbol.")
            elif any(cs.lower() in test_id.lower() for cs in changed_symbols):
                f_direct = 0.6
                is_directly_affected = True
                explanations.append("Test identifier references modified source symbol name.")

            score_components += self.WEIGHT_DIRECT_CODE * f_direct

            # 2. Requirement relationship component (weight 0.25)
            # Find links verifying requirements
            test_links = [
                l for l in links
                if l.artifact_path.replace("\\", "/") == file_path and "test" in l.link_type.value
            ]

            f_req = 0.0
            linked_req_id = None
            req_priority_str = "medium"

            for l in test_links:
                if l.requirement_id in direct_req_ids:
                    f_req = 1.0
                    linked_req_id = l.requirement_id
                    req_priority_str = direct_req_ids[l.requirement_id].priority
                    explanations.append(
                        f"Verifies directly affected requirement {l.requirement_id} ('{direct_req_ids[l.requirement_id].title}')."
                    )
                    break
                elif l.requirement_id in downstream_req_ids:
                    f_req = max(f_req, 0.70)
                    linked_req_id = l.requirement_id
                    req_priority_str = downstream_req_ids[l.requirement_id].priority
                    explanations.append(
                        f"Verifies downstream requirement {l.requirement_id} impacted by dependency blast-radius."
                    )

            score_components += self.WEIGHT_REQUIREMENT * f_req

            # 3. Requirement priority component (weight 0.15)
            p_weight = self.PRIORITY_WEIGHTS.get(req_priority_str.lower(), 0.35)
            score_components += self.WEIGHT_PRIORITY * p_weight
            if linked_req_id:
                explanations.append(f"Requirement priority is {req_priority_str.upper()} (weight {p_weight}).")

            # 4. Blast radius depth component (weight 0.15)
            depth_factor = min(1.0, impact.max_blast_radius_depth / 3.0)
            score_components += self.WEIGHT_BLAST_RADIUS * depth_factor
            if impact.max_blast_radius_depth > 0 and f_req > 0:
                explanations.append(f"Subject to dependency blast-radius depth {impact.max_blast_radius_depth}.")

            # 5. Historical reliability component (weight 0.10)
            has_hist, fail_rate, avg_dur = self.history_repo.get_test_stats(test_id)
            if has_hist:
                score_components += self.WEIGHT_HISTORY * fail_rate
                explanations.append(f"Historical failure rate: {round(fail_rate * 100, 1)}% across previous verification runs.")
            else:
                explanations.append("No prior execution history recorded; historical success was not assumed.")

            final_score = round(max(0.05, min(1.0, score_components)), 4)

            scored_items.append(
                RankedTestItem(
                    rank=0,  # Assigned after sorting
                    test_id=test_id,
                    file_path=file_path,
                    symbol_name=symbol_name,
                    score=final_score,
                    predicted_failure_probability=None,
                    confidence=1.0,
                    explanations=explanations,
                    is_directly_affected=is_directly_affected,
                    verifies_requirement_id=linked_req_id,
                    historical_failure_rate=fail_rate if has_hist else None,
                    historical_duration_ms=avg_dur if has_hist else None,
                    method="deterministic_baseline",
                    is_selected=True,
                )
            )

        # Sort descending by score, tie-break by test_id
        scored_items.sort(key=lambda x: (-x.score, x.test_id))

        # Assign ranks
        for idx, item in enumerate(scored_items):
            item.rank = idx + 1

        return scored_items
