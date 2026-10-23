"""
Predictive Regression Model Wrapper.
Manages serialized scikit-learn models, inference pipelines, metadata inspection,
and honest fallback to deterministic prioritization when no trained weights exist.
"""

import json
import os
from typing import Any, Dict, List, Optional
import joblib
from ai.regression_model.schema import RegressionFeatureVector


def resolve_regression_model_path(relative_path: str = "ai/models/regression_model_v1.joblib") -> str:
    """Resolves model artifact file path across root and backend working directories."""
    if os.path.isabs(relative_path) and os.path.exists(relative_path):
        return relative_path

    # Candidate 1: relative to current working directory
    cand1 = os.path.abspath(relative_path)
    if os.path.exists(cand1):
        return cand1

    # Candidate 2: relative to this file's root (ai/regression_model -> root)
    module_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(module_dir, "..", ".."))
    cand2 = os.path.abspath(os.path.join(root_dir, relative_path))
    if os.path.exists(cand2):
        return cand2

    return cand1


class PredictiveRegressionModel:
    """
    Task-specific ML model for predicting the probability that a test detects a regression.
    Strictly reports status='not_trained' and falls back to deterministic scoring
    when valid trained checkpoint weights are missing.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.target_path = model_path or "ai/models/regression_model_v1.joblib"
        self.resolved_path = resolve_regression_model_path(self.target_path)
        self.model = None
        self.metadata: Dict[str, Any] = {}
        self._load_model()

    def _load_model(self) -> None:
        """Loads model weights and companion metadata if file exists."""
        if os.path.exists(self.resolved_path):
            try:
                self.model = joblib.load(self.resolved_path)
                meta_path = self.resolved_path.replace(".joblib", "_metadata.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
            except Exception:
                self.model = None

    @property
    def is_trained(self) -> bool:
        """Returns True only when valid serialized weights are loaded into memory."""
        return self.model is not None

    def predict_risk(self, features: RegressionFeatureVector) -> Dict[str, Any]:
        """
        Estimates the probability that this test will fail / detect a fault for the change.
        If untrained, provides truthful deterministic fallback and marks is_baseline=True.
        """
        feature_array = features.to_array()

        if not self.is_trained:
            # Deterministic baseline formula as fallback
            score = (
                0.35 * (1.0 if features.is_direct_test_change or features.symbol_overlap_count > 0 else 0.0)
                + 0.25 * (1.0 if features.dependency_distance == 0 else max(0.0, 1.0 - 0.25 * features.dependency_distance))
                + 0.15 * features.requirement_priority_weight
                + 0.15 * min(1.0, features.blast_radius_depth / 3.0)
                + 0.10 * (features.historical_failure_rate if features.has_historical_data else 0.0)
            )
            score = round(max(0.0, min(1.0, score)), 4)
            return {
                "probability": score,
                "score": score,
                "method": "deterministic_fallback",
                "is_baseline": True,
                "model_status": "not_trained",
                "model_name": "deterministic_baseline_fallback",
                "model_version": "v1.0.0-untrained",
            }

        try:
            # Model predict_proba returns [P(outcome=0), P(outcome=1)]
            probas = self.model.predict_proba([feature_array])[0]
            # Check classes ordering
            classes = list(self.model.classes_)
            if 1 in classes:
                pos_idx = classes.index(1)
                prob_failure = round(float(probas[pos_idx]), 4)
            else:
                prob_failure = round(float(probas[-1]), 4)

            return {
                "probability": prob_failure,
                "score": prob_failure,
                "method": "predictive_ml",
                "is_baseline": False,
                "model_status": "trained",
                "model_name": self.metadata.get("algorithm", "random_forest"),
                "model_version": self.metadata.get("version", "v1.0.0"),
            }
        except Exception:
            # Safety fallback on prediction exception
            return {
                "probability": 0.5,
                "score": 0.5,
                "method": "deterministic_fallback",
                "is_baseline": True,
                "model_status": "error_fallback",
                "model_name": "error_fallback",
                "model_version": "v1.0.0-fallback",
            }

    def get_metadata(self) -> Dict[str, Any]:
        """Returns comprehensive diagnostic and metadata report."""
        if not self.is_trained:
            return {
                "model_name": "PredictiveRegressionModel",
                "status": "not_trained",
                "is_trained": False,
                "resolved_path": self.resolved_path,
                "version": "v1.0.0-untrained",
                "features_expected": RegressionFeatureVector.feature_names(),
                "fallback_behavior": "Explainable deterministic scoring baseline active",
                "notes": "No trained model weights found at resolved path. System transparently uses deterministic prioritization.",
            }

        return {
            "model_name": self.metadata.get("name", "PredictiveRegressionModel"),
            "status": "trained",
            "is_trained": True,
            "resolved_path": self.resolved_path,
            "version": self.metadata.get("version", "v1.0.0"),
            "algorithm": self.metadata.get("algorithm", "RandomForestClassifier"),
            "trained_at": self.metadata.get("trained_at"),
            "training_sample_count": self.metadata.get("sample_count", 0),
            "features_expected": RegressionFeatureVector.feature_names(),
            "provenance_breakdown": self.metadata.get("provenance_breakdown", {}),
            "evaluation_metrics": self.metadata.get("evaluation_metrics", {}),
            "fallback_behavior": "Predictive ML active with deterministic fallback on missing features",
        }
