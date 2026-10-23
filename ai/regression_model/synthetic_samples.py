"""
Synthetic sample generator for Predictive Regression Testing pipeline tests.
IMPORTANT: All samples generated here have is_synthetic=True and
provenance='synthetic_pipeline_test'. They are strictly intended for testing
the training, evaluation, and data-leakage verification pipelines, and are
NEVER represented as real-world benchmark evaluations.
"""

from datetime import datetime, timezone
from typing import List
from ai.regression_model.schema import RegressionFeatureVector, TestExecutionObservation


def generate_synthetic_training_samples(count: int = 40) -> List[TestExecutionObservation]:
    """
    Generates a synthetic dataset with diverse changes and balanced classes
    for validating the ML pipeline on CPU without network calls or external data.
    """
    samples: List[TestExecutionObservation] = []
    now = datetime.now(timezone.utc).isoformat()

    for i in range(count):
        change_group = f"CHG-{(i // 4) + 1:03d}"
        is_regression = (i % 2 == 0)

        if is_regression:
            # Typical features for regression-detecting tests
            feat = RegressionFeatureVector(
                change_file_count=2,
                is_direct_test_change=1 if (i % 4 == 0) else 0,
                symbol_overlap_count=3 if (i % 4 == 0) else 1,
                requirement_priority_weight=1.0 if (i % 3 == 0) else 0.75,
                dependency_distance=0 if (i % 4 == 0) else 1,
                blast_radius_depth=2,
                is_confirmed_link=1,
                historical_failure_rate=0.4,
                has_historical_data=1,
                historical_duration_normalized=0.15,
            )
            outcome = 1
        else:
            # Typical features for passing/unaffected tests
            feat = RegressionFeatureVector(
                change_file_count=1,
                is_direct_test_change=0,
                symbol_overlap_count=0,
                requirement_priority_weight=0.25,
                dependency_distance=3,
                blast_radius_depth=0,
                is_confirmed_link=0,
                historical_failure_rate=0.0,
                has_historical_data=1,
                historical_duration_normalized=0.05,
            )
            outcome = 0

        samples.append(
            TestExecutionObservation(
                observation_id=f"SYN-OBS-{i+1:04d}",
                change_id=change_group,
                project_id="PROJ-SYNTHETIC",
                test_id=f"tests/test_module_{i % 8}.py::test_case_{i % 16}",
                outcome=outcome,
                features=feat,
                label_provenance="synthetic_pipeline_test",
                is_synthetic=True,
                timestamp=now,
            )
        )

    return samples


def generate_single_class_samples(count: int = 15, outcome: int = 0) -> List[TestExecutionObservation]:
    """Generates synthetic samples where all outcomes are identical to test edge cases."""
    samples: List[TestExecutionObservation] = []
    now = datetime.now(timezone.utc).isoformat()

    for i in range(count):
        samples.append(
            TestExecutionObservation(
                observation_id=f"SYN-SC-{i+1:04d}",
                change_id=f"CHG-{(i // 3) + 1:03d}",
                project_id="PROJ-SYNTHETIC",
                test_id=f"tests/test_single.py::test_{i}",
                outcome=outcome,
                features=RegressionFeatureVector(),
                label_provenance="synthetic_pipeline_test",
                is_synthetic=True,
                timestamp=now,
            )
        )
    return samples
