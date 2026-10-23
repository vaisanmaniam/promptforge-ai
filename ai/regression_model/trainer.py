"""
Model Training Pipeline for Predictive Regression Testing.
Validates datasets, prevents data leakage via change-level grouping,
guards against single-class/insufficient-data hazards, and serializes trained models with metadata.
"""

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ai.regression_model.model import resolve_regression_model_path
from ai.regression_model.schema import DatasetSummary, RegressionFeatureVector, TestExecutionObservation


class ModelTrainingPipeline:
    """
    Handles validation, change-level train/validation splitting, model training,
    and checkpoint serialization with comprehensive provenance tracking.
    """

    MIN_SAMPLES_THRESHOLD = 10

    def summarize_dataset(self, observations: List[TestExecutionObservation]) -> DatasetSummary:
        """Computes statistical summary and validation checks for observation dataset."""
        total = len(observations)
        if total == 0:
            return DatasetSummary(
                total_samples=0,
                positive_count=0,
                negative_count=0,
                positive_ratio=0.0,
                unique_changes=0,
                unique_projects=0,
                provenance_counts={},
                has_synthetic=False,
                status="insufficient_data",
            )

        positives = sum(1 for o in observations if o.outcome == 1)
        negatives = total - positives
        pos_ratio = round(positives / total, 4)

        unique_changes = len(set(o.change_id for o in observations))
        unique_projects = len(set(o.project_id for o in observations))
        provenance_counts = dict(Counter(o.label_provenance for o in observations))
        has_synthetic = any(o.is_synthetic for o in observations)

        status = "valid"
        if total < self.MIN_SAMPLES_THRESHOLD:
            status = "insufficient_data"
        elif positives == 0 or negatives == 0:
            status = "single_class_detected"

        return DatasetSummary(
            total_samples=total,
            positive_count=positives,
            negative_count=negatives,
            positive_ratio=pos_ratio,
            unique_changes=unique_changes,
            unique_projects=unique_projects,
            provenance_counts=provenance_counts,
            has_synthetic=has_synthetic,
            status=status,
        )

    def _split_by_change_group(
        self, observations: List[TestExecutionObservation], test_ratio: float = 0.25
    ) -> Tuple[List[TestExecutionObservation], List[TestExecutionObservation]]:
        """
        Splits dataset by change_id to strictly prevent data leakage between train and test sets.
        All observations belonging to the same change are placed entirely in train OR test.
        """
        changes = sorted(list(set(o.change_id for o in observations)))
        if len(changes) <= 1:
            # Cannot group-split single change; split observations directly
            split_idx = max(1, int(len(observations) * (1.0 - test_ratio)))
            return observations[:split_idx], observations[split_idx:]

        test_change_count = max(1, int(len(changes) * test_ratio))
        # Deterministic pseudo-random pick by stride
        test_changes = set(changes[::max(1, len(changes) // test_change_count)][:test_change_count])
        train_obs = [o for o in observations if o.change_id not in test_changes]
        test_obs = [o for o in observations if o.change_id in test_changes]

        # Verify neither split is completely empty
        if not train_obs:
            train_obs = test_obs[: len(test_obs) // 2]
            test_obs = test_obs[len(test_obs) // 2 :]

        return train_obs, test_obs

    def train_and_persist(
        self,
        observations: List[TestExecutionObservation],
        model_path: Optional[str] = None,
        algorithm: str = "RandomForestClassifier",
    ) -> Dict[str, Any]:
        """
        Validates observations, trains the predictive model, and saves weights + companion metadata.
        Returns a detailed report.
        """
        summary = self.summarize_dataset(observations)
        if summary.status != "valid":
            return {
                "success": False,
                "status": summary.status,
                "message": (
                    f"Dataset is not eligible for training: {summary.status}. "
                    f"Required: >= {self.MIN_SAMPLES_THRESHOLD} samples with both positive and negative outcomes. "
                    f"Found: {summary.total_samples} samples (positives={summary.positive_count}, negatives={summary.negative_count})."
                ),
                "dataset_summary": summary.model_dump(),
            }

        # Change-grouped split
        train_obs, test_obs = self._split_by_change_group(observations)

        X_train = np.array([o.features.to_array() for o in train_obs])
        y_train = np.array([o.outcome for o in train_obs])

        # Initialize model
        if algorithm == "LogisticRegression":
            clf = LogisticRegression(class_weight="balanced", max_iter=200, random_state=42)
        else:
            clf = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                class_weight="balanced",
                random_state=42,
            )

        clf.fit(X_train, y_train)

        # Basic held-out metrics if test set has both classes
        eval_metrics: Dict[str, Any] = {}
        if test_obs:
            from ai.regression_model.evaluator import ModelEvaluationPipeline
            evaluator = ModelEvaluationPipeline()
            eval_res = evaluator.evaluate(clf, test_obs)
            eval_metrics = eval_res.get("metrics", {})

        # Resolve destination path
        target_path = model_path or "ai/models/regression_model_v1.joblib"
        resolved_path = resolve_regression_model_path(target_path)
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)

        joblib.dump(clf, resolved_path)

        # Companion metadata
        meta = {
            "name": "PredictiveRegressionModel",
            "version": "v1.0.0",
            "algorithm": algorithm,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(observations),
            "train_sample_count": len(train_obs),
            "test_sample_count": len(test_obs),
            "features": RegressionFeatureVector.feature_names(),
            "provenance_breakdown": summary.provenance_counts,
            "has_synthetic_data": summary.has_synthetic,
            "dataset_summary": summary.model_dump(),
            "evaluation_metrics": eval_metrics,
        }
        meta_path = resolved_path.replace(".joblib", "_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return {
            "success": True,
            "status": "trained",
            "message": f"Successfully trained and persisted model to {resolved_path}",
            "saved_model_path": resolved_path,
            "metadata_path": meta_path,
            "dataset_summary": summary.model_dump(),
            "evaluation_metrics": eval_metrics,
        }
