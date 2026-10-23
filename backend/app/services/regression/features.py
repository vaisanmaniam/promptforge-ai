"""
Feature Extraction Adapter for Predictive Regression Testing.
Transforms change impact reports, AST artifacts, and requirement graph topologies
into standard RegressionFeatureVector representations for scikit-learn models.
"""

from typing import Dict, List, Optional
from ai.regression_model.schema import RegressionFeatureVector
from app.schemas.regression import ChangeImpactReport, RankedTestItem
from app.schemas.requirement import RequirementSpecification
from app.schemas.verification import ArtifactMetadata, FileType, ProjectIngestionReport, TraceabilityLink
from app.services.regression.history import TestHistoryRepository


class RegressionFeatureExtractor:
    """
    Extracts numerical feature representations for (change, test) candidate pairs.
    """

    def __init__(self, history_repo: Optional[TestHistoryRepository] = None):
        self.history_repo = history_repo or TestHistoryRepository()

    def extract_features(
        self,
        test_id: str,
        file_path: str,
        symbol_name: Optional[str],
        impact: ChangeImpactReport,
        links: List[TraceabilityLink],
        spec: Optional[RequirementSpecification] = None,
    ) -> RegressionFeatureVector:
        """
        Builds a normalized RegressionFeatureVector for a specific test candidate.
        """
        changed_paths = {c.file_path for c in impact.changed_files}
        changed_symbols = set(impact.changed_symbols)

        # 1. change_file_count
        change_file_count = max(1, len(impact.changed_files))

        # 2. is_direct_test_change
        is_direct_test = 1 if file_path in changed_paths else 0

        # 3. symbol_overlap_count
        symbol_overlap = 0
        if symbol_name:
            for cs in changed_symbols:
                if cs.lower() in symbol_name.lower():
                    symbol_overlap += 1
        for cs in changed_symbols:
            if cs.lower() in test_id.lower():
                symbol_overlap += 1

        # 4. requirement_priority_weight & dependency_distance & is_confirmed_link
        req_priority_weight = 0.35
        dep_distance = 3
        is_confirmed = 0

        direct_req_ids = {r.requirement_id: r for r in impact.directly_affected_requirements}
        downstream_req_ids = {r.requirement_id: r for r in impact.downstream_affected_requirements}

        test_links = [
            l for l in links
            if l.artifact_path.replace("\\", "/") == file_path and "test" in l.link_type.value
        ]

        priority_map = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}

        for l in test_links:
            if l.is_confirmed:
                is_confirmed = 1

            if l.requirement_id in direct_req_ids:
                dep_distance = 0
                r_info = direct_req_ids[l.requirement_id]
                req_priority_weight = priority_map.get(r_info.priority.lower(), 0.5)
                break
            elif l.requirement_id in downstream_req_ids:
                dep_distance = min(dep_distance, 1)
                r_info = downstream_req_ids[l.requirement_id]
                req_priority_weight = max(req_priority_weight, priority_map.get(r_info.priority.lower(), 0.5))

        # 5. blast_radius_depth
        blast_depth = impact.max_blast_radius_depth

        # 6. Historical statistics
        has_hist, fail_rate, avg_dur = self.history_repo.get_test_stats(test_id)
        has_hist_val = 1 if has_hist else 0
        dur_norm = round(min(1.0, avg_dur / 5000.0), 4) if has_hist else 0.0

        return RegressionFeatureVector(
            change_file_count=change_file_count,
            is_direct_test_change=is_direct_test,
            symbol_overlap_count=symbol_overlap,
            requirement_priority_weight=round(req_priority_weight, 4),
            dependency_distance=dep_distance,
            blast_radius_depth=blast_depth,
            is_confirmed_link=is_confirmed,
            historical_failure_rate=round(fail_rate, 4),
            has_historical_data=has_hist_val,
            historical_duration_normalized=dur_norm,
        )
