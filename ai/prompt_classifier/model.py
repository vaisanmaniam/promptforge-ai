import json
import os
from typing import Any, Dict, Optional
import joblib
from ai.prompt_classifier.base import BasePromptClassifier, ClassificationResult
from ai.prompt_classifier.rules import RuleBasedClassifier


def resolve_model_path(relative_path: str = "ai/models/prompt_classifier_v1.joblib") -> str:
    """Resolves model artifact file path across root and backend working directories."""
    if os.path.isabs(relative_path) and os.path.exists(relative_path):
        return relative_path

    # Candidate 1: relative to current working directory
    cand1 = os.path.abspath(relative_path)
    if os.path.exists(cand1):
        return cand1

    # Candidate 2: relative to this file's root (ai/prompt_classifier -> root)
    module_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(module_dir, "..", ".."))
    cand2 = os.path.abspath(os.path.join(root_dir, relative_path))
    if os.path.exists(cand2):
        return cand2

    return cand1


class SklearnPromptClassifier(BasePromptClassifier):
    """
    Scikit-learn TF-IDF + Logistic Regression prompt classifier.
    Gracefully falls back to RuleBasedClassifier when trained weights are missing.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.target_path = model_path or "ai/models/prompt_classifier_v1.joblib"
        self.resolved_path = resolve_model_path(self.target_path)
        self.pipeline = None
        self.metadata = {}
        self.fallback = RuleBasedClassifier()
        self._load_model()

    def _load_model(self) -> None:
        if os.path.exists(self.resolved_path):
            try:
                self.pipeline = joblib.load(self.resolved_path)
                # Load metadata companion if present
                meta_path = self.resolved_path.replace(".joblib", "_metadata.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
            except Exception:
                self.pipeline = None

    @property
    def is_trained(self) -> bool:
        return self.pipeline is not None

    def predict_proba(self, prompt: str) -> Dict[str, float]:
        if not self.is_trained:
            return self.fallback.predict_proba(prompt)

        classes = list(self.pipeline.classes_)
        proba_matrix = self.pipeline.predict_proba([prompt])[0]
        return {cls_name: round(float(prob), 4) for cls_name, prob in zip(classes, proba_matrix)}

    def predict(self, prompt: str) -> ClassificationResult:
        if not self.is_trained:
            res = self.fallback.predict(prompt)
            return ClassificationResult(
                predicted_category=res.predicted_category,
                confidence=res.confidence,
                probabilities=res.probabilities,
                model_name="rule_based_fallback_classifier",
                model_version="v1.0.0-untrained",
                method="untrained_baseline",
                is_baseline=True,
            )

        probs = self.predict_proba(prompt)
        best_cat = max(probs, key=probs.get)
        confidence = probs[best_cat]

        return ClassificationResult(
            predicted_category=best_cat,
            confidence=confidence,
            probabilities=probs,
            model_name="tfidf_logistic_regression",
            model_version=self.metadata.get("version", "v1.0.0"),
            method="ml_model",
            is_baseline=False,
        )

    def get_metadata(self) -> Dict[str, Any]:
        if not self.is_trained:
            return {
                "name": "SklearnPromptClassifier",
                "status": "untrained",
                "resolved_path": self.resolved_path,
                "fallback": self.fallback.get_metadata(),
            }
        return {
            "name": "SklearnPromptClassifier",
            "status": "trained",
            "resolved_path": self.resolved_path,
            "classes": list(self.pipeline.classes_) if self.pipeline else [],
            "training_metadata": self.metadata,
        }
