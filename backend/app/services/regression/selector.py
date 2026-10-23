"""
Test Selection and Prioritization Orchestrator.
Supports all_tests, impact_based, and predictive strategies with top-k and execution budget bounds,
explicit exclusion rationales, and seamless delegation to the Phase 4 isolated Docker runner.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from ai.regression_model.model import PredictiveRegressionModel
from app.schemas.regression import (
    ChangeImpactReport,
    ExcludedTestItem,
    PrioritizationReport,
    PrioritizationStrategy,
    RankedTestItem,
    TestSelectionReport,
)
from app.schemas.requirement import RequirementSpecification
from app.schemas.verification import ProjectIngestionReport, TraceabilityLink, VerificationRun
from app.services.regression.baseline import DeterministicPrioritizer
from app.services.regression.features import RegressionFeatureExtractor
from app.services.verification.engine import VerificationEngine


class TestSelector:
    """
    Coordinates test prioritization, budget-based selection, and Docker verification runs.
    """
    __test__ = False

    def __init__(
        self,
        baseline: Optional[DeterministicPrioritizer] = None,
        ml_model: Optional[PredictiveRegressionModel] = None,
        feature_extractor: Optional[RegressionFeatureExtractor] = None,
        verification_engine: Optional[VerificationEngine] = None,
        history_repo: Optional[Any] = None,
    ):
        self.baseline = baseline or DeterministicPrioritizer(history_repo=history_repo)
        self.ml_model = ml_model or PredictiveRegressionModel()
        self.feature_extractor = feature_extractor or RegressionFeatureExtractor(history_repo=history_repo)
        self.verification_engine = verification_engine or VerificationEngine()

    def prioritize_tests(
        self,
        impact: ChangeImpactReport,
        project: ProjectIngestionReport,
        links: List[TraceabilityLink],
        spec: Optional[RequirementSpecification] = None,
        strategy: PrioritizationStrategy = PrioritizationStrategy.PREDICTIVE,
        discovered_test_nodes: Optional[List[str]] = None,
    ) -> PrioritizationReport:
        """
        Ranks all discovered tests according to the chosen strategy.
        Transparently falls back to deterministic scoring when the predictive model is untrained.
        """
        now = datetime.now(timezone.utc).isoformat()
        ranked_baseline = self.baseline.rank_tests(
            impact=impact,
            project=project,
            links=links,
            spec=spec,
            discovered_test_nodes=discovered_test_nodes,
        )

        total_tests = len(ranked_baseline)
        fallback = False
        fallback_reason = None
        final_ranked: List[RankedTestItem] = []

        if strategy == PrioritizationStrategy.ALL_TESTS:
            # All tests strategy: preserves baseline risk indicators but treats all as eligible
            final_ranked = ranked_baseline
        elif strategy == PrioritizationStrategy.IMPACT_BASED:
            # Impact-based: direct change or affected requirement gets high rank, others scored low
            final_ranked = ranked_baseline
        elif strategy == PrioritizationStrategy.PREDICTIVE:
            if not self.ml_model.is_trained:
                fallback = True
                fallback_reason = (
                    "Predictive ML model weights not trained. Falling back to explainable deterministic baseline."
                )
                final_ranked = ranked_baseline
            else:
                # Use trained ML model
                ml_ranked = []
                for item in ranked_baseline:
                    features = self.feature_extractor.extract_features(
                        test_id=item.test_id,
                        file_path=item.file_path,
                        symbol_name=item.symbol_name,
                        impact=impact,
                        links=links,
                        spec=spec,
                    )
                    pred = self.ml_model.predict_risk(features)
                    item.predicted_failure_probability = pred["probability"]
                    item.score = pred["score"]
                    item.method = pred["method"]
                    item.explanations.insert(
                        0,
                        f"Predictive ML estimated regression detection probability: {round(pred['probability'] * 100, 1)}%",
                    )
                    ml_ranked.append(item)

                # Re-sort by ML score
                ml_ranked.sort(key=lambda x: (-x.score, x.test_id))
                for idx, item in enumerate(ml_ranked):
                    item.rank = idx + 1
                final_ranked = ml_ranked

        return PrioritizationReport(
            analysis_id=impact.analysis_id,
            project_id=impact.project_id,
            strategy_used=strategy,
            fallback_to_baseline=fallback,
            fallback_reason=fallback_reason,
            model_status="trained" if self.ml_model.is_trained else "not_trained",
            total_tests_discovered=total_tests,
            ranked_tests=final_ranked,
            created_at=now,
        )

    def select_tests(
        self,
        impact: ChangeImpactReport,
        project: ProjectIngestionReport,
        links: List[TraceabilityLink],
        spec: Optional[RequirementSpecification] = None,
        strategy: PrioritizationStrategy = PrioritizationStrategy.PREDICTIVE,
        top_k: Optional[int] = None,
        execution_budget_ms: Optional[float] = None,
        discovered_test_nodes: Optional[List[str]] = None,
    ) -> TestSelectionReport:
        """
        Applies strategy filtering, top-k caps, and execution budget limits.
        Categorizes items into selected_tests and excluded_tests with clear reasons.
        """
        p_report = self.prioritize_tests(
            impact=impact,
            project=project,
            links=links,
            spec=spec,
            strategy=strategy,
            discovered_test_nodes=discovered_test_nodes,
        )

        selected: List[RankedTestItem] = []
        excluded: List[ExcludedTestItem] = []
        cumulative_duration_ms: float = 0.0

        for item in p_report.ranked_tests:
            # Estimate test duration (from history or default 50ms)
            test_dur = item.historical_duration_ms if (item.historical_duration_ms and item.historical_duration_ms > 0) else 50.0

            # 1. Strategy exclusion check
            if strategy == PrioritizationStrategy.IMPACT_BASED:
                # If test has neither direct change nor linked requirement nor symbol match, exclude
                if not item.is_directly_affected and not item.verifies_requirement_id and item.score < 0.20:
                    excluded.append(
                        ExcludedTestItem(
                            test_id=item.test_id,
                            rank=item.rank,
                            score=item.score,
                            exclusion_reason="Zero structural or requirement impact detected from current change set.",
                        )
                    )
                    continue

            # 2. Top-k check
            if top_k is not None and len(selected) >= top_k:
                excluded.append(
                    ExcludedTestItem(
                        test_id=item.test_id,
                        rank=item.rank,
                        score=item.score,
                        exclusion_reason=f"Exceeded Top-{top_k} selection limit (ranked #{item.rank} with score {item.score}).",
                    )
                )
                continue

            # 3. Execution budget check
            if execution_budget_ms is not None and (cumulative_duration_ms + test_dur > execution_budget_ms) and len(selected) > 0:
                excluded.append(
                    ExcludedTestItem(
                        test_id=item.test_id,
                        rank=item.rank,
                        score=item.score,
                        exclusion_reason=(
                            f"Exceeded execution time budget of {execution_budget_ms}ms "
                            f"(cumulative {round(cumulative_duration_ms + test_dur, 1)}ms)."
                        ),
                    )
                )
                continue

            # Selected!
            cumulative_duration_ms += test_dur
            selected.append(item)

        return TestSelectionReport(
            analysis_id=impact.analysis_id,
            project_id=impact.project_id,
            strategy=strategy,
            total_tests=len(p_report.ranked_tests),
            selected_count=len(selected),
            excluded_count=len(excluded),
            selected_tests=selected,
            excluded_tests=excluded,
            estimated_duration_ms=round(cumulative_duration_ms, 2),
            fallback_to_baseline=p_report.fallback_to_baseline,
            fallback_reason=p_report.fallback_reason,
            created_at=p_report.created_at,
        )
