"""
Historical Test Result Collector and Storage Repository.
Extracts and maintains genuine test execution observations from Phase 4 verification runs,
tracks per-test failure frequency and execution duration, handles renames/duplicates,
and supports local JSON fallback persistence.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ai.regression_model.schema import (
    DatasetSummary,
    RegressionFeatureVector,
    TestExecutionObservation,
)
from ai.regression_model.synthetic_samples import generate_synthetic_training_samples
from app.core.logging import logger
from app.schemas.regression import HistoricalObservationSummary
from app.schemas.verification import VerificationRun

REGRESSION_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "regression"


class TestHistoryRepository:
    """
    Collects, aggregates, and serves historical test execution observations.
    """
    __test__ = False

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or REGRESSION_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.obs_file = self.data_dir / "observations.json"
        self._observations: List[TestExecutionObservation] = []
        self._load()

    def _load(self) -> None:
        """Loads observations from local JSON disk storage."""
        if self.obs_file.exists():
            try:
                with open(self.obs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._observations = [TestExecutionObservation.model_validate(d) for d in data]
            except Exception as e:
                logger.warning(f"Failed to read observations file: {e}")
                self._observations = []

    def _save(self) -> None:
        """Persists observations to local JSON disk storage."""
        try:
            with open(self.obs_file, "w", encoding="utf-8") as f:
                json.dump([o.model_dump() for o in self._observations], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save observations file: {e}")

    def add_observation(self, observation: TestExecutionObservation) -> None:
        """Adds a single observation, updating if identical observation_id already exists."""
        idx = next((i for i, o in enumerate(self._observations) if o.observation_id == observation.observation_id), None)
        if idx is not None:
            self._observations[idx] = observation
        else:
            self._observations.append(observation)
        self._save()

    def add_observations_batch(self, observations: List[TestExecutionObservation]) -> int:
        """Adds a batch of observations."""
        added = 0
        existing_ids = {o.observation_id for o in self._observations}
        for o in observations:
            if o.observation_id in existing_ids:
                # Update
                idx = next(i for i, x in enumerate(self._observations) if x.observation_id == o.observation_id)
                self._observations[idx] = o
            else:
                self._observations.append(o)
                existing_ids.add(o.observation_id)
            added += 1
        self._save()
        return added

    def record_verification_run(
        self,
        run: VerificationRun,
        features_map: Optional[Dict[str, RegressionFeatureVector]] = None,
    ) -> List[TestExecutionObservation]:
        """
        Extracts genuine test outcome observations from a completed Phase 4 VerificationRun.
        """
        now = datetime.now(timezone.utc).isoformat()
        new_obs: List[TestExecutionObservation] = []

        # From run, we have passed and failed test names
        # e.g., parsed passed tests and failed tests
        passed_tests = []
        failed_tests = []

        # Parse from requirement verdicts or stdout if lists are empty
        for verdict in run.requirement_verdicts.values():
            passed_tests.extend(verdict.passed_tests)
            failed_tests.extend(verdict.failed_tests)

        # Deduplicate
        passed_tests = sorted(list(set(passed_tests)))
        failed_tests = sorted(list(set(failed_tests)))

        # Record failed tests (outcome=1)
        for i, test_id in enumerate(failed_tests):
            obs_id = f"RUN-{run.id[:8]}-FAIL-{i+1}"
            features = (features_map or {}).get(test_id, RegressionFeatureVector())
            obs = TestExecutionObservation(
                observation_id=obs_id,
                change_id=run.id,
                project_id=run.project_id,
                test_id=test_id,
                outcome=1,
                features=features,
                label_provenance="docker_verification_run",
                is_synthetic=False,
                timestamp=now,
            )
            new_obs.append(obs)

        # Record passed tests (outcome=0)
        for i, test_id in enumerate(passed_tests):
            obs_id = f"RUN-{run.id[:8]}-PASS-{i+1}"
            features = (features_map or {}).get(test_id, RegressionFeatureVector())
            obs = TestExecutionObservation(
                observation_id=obs_id,
                change_id=run.id,
                project_id=run.project_id,
                test_id=test_id,
                outcome=0,
                features=features,
                label_provenance="docker_verification_run",
                is_synthetic=False,
                timestamp=now,
            )
            new_obs.append(obs)

        if new_obs:
            self.add_observations_batch(new_obs)

        return new_obs

    def get_test_stats(self, test_id: str) -> Tuple[bool, float, float]:
        """
        Returns (has_history, failure_rate, average_duration_ms) for a specific test.
        If no history exists, returns (False, 0.0, 0.0) without assuming success.
        """
        matching = [o for o in self._observations if o.test_id == test_id or test_id in o.test_id]
        if not matching:
            return False, 0.0, 0.0

        failures = sum(1 for o in matching if o.outcome == 1)
        failure_rate = round(failures / len(matching), 4)

        durations = [o.features.historical_duration_normalized * 1000.0 for o in matching if o.features.historical_duration_normalized > 0]
        avg_dur = round(sum(durations) / len(durations), 2) if durations else 50.0

        return True, failure_rate, avg_dur

    def get_observations(
        self,
        project_id: Optional[str] = None,
        include_synthetic: bool = False,
    ) -> List[TestExecutionObservation]:
        """Filters observations by project and synthetic inclusion."""
        results = self._observations
        if not include_synthetic:
            results = [o for o in results if not o.is_synthetic]
        if project_id:
            results = [o for o in results if o.project_id == project_id]
        return results

    def get_summary(self, project_id: Optional[str] = None) -> HistoricalObservationSummary:
        """Returns aggregate telemetry over collected historical observations."""
        obs = self.get_observations(project_id=project_id, include_synthetic=False)
        total = len(obs)
        unique_tests = len(set(o.test_id for o in obs))
        unique_changes = len(set(o.change_id for o in obs))
        failed_count = sum(1 for o in obs if o.outcome == 1)
        passed_count = total - failed_count

        prov_dist: Dict[str, int] = {}
        for o in obs:
            prov_dist[o.label_provenance] = prov_dist.get(o.label_provenance, 0) + 1

        return HistoricalObservationSummary(
            total_observations=total,
            unique_tests=unique_tests,
            unique_changes=unique_changes,
            passed_count=passed_count,
            failed_count=failed_count,
            has_genuine_failures=failed_count > 0,
            provenance_distribution=prov_dist,
        )

    def load_synthetic_test_pipeline_samples(self, count: int = 40) -> int:
        """Loads clearly marked synthetic samples for testing the training/eval pipelines."""
        samples = generate_synthetic_training_samples(count=count)
        return self.add_observations_batch(samples)
