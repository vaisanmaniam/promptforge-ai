"""
Model Evaluation Pipeline for Predictive Regression Testing.
Computes precision, recall, F1, PR-AUC, and Top-K fault recall on held-out test splits.
Provides side-by-side comparison against the deterministic baseline and handles
insufficient-data / single-class scenarios honestly.
"""

from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from ai.regression_model.schema import DatasetSummary, RegressionFeatureVector, TestExecutionObservation


class ModelEvaluationPipeline:
    """
    Evaluates trained predictive models against held-out observations and benchmarks
    against the deterministic baseline.
    """

    def evaluate(
        self,
        model: Any,
        test_observations: List[TestExecutionObservation],
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Runs comprehensive evaluation.
        If dataset is too small (< 5 samples) or has only one class, returns status='insufficient_data'.
        """
        if len(test_observations) < 5:
            return {
                "status": "insufficient_data",
                "message": f"Held-out evaluation set contains only {len(test_observations)} observations. Minimum required: 5.",
                "sample_count": len(test_observations),
                "metrics": {},
            }

        y_true = np.array([o.outcome for o in test_observations])
        unique_classes = set(y_true)
        if len(unique_classes) < 2:
            return {
                "status": "single_class_detected",
                "message": "Held-out evaluation set contains only one class. Multi-class metrics (precision, recall, F1) cannot be computed meaningfully.",
                "sample_count": len(test_observations),
                "classes": list(unique_classes),
                "metrics": {},
            }

        X_test = np.array([o.features.to_array() for o in test_observations])

        # Model predictions
        try:
            probas = model.predict_proba(X_test)
            classes = list(model.classes_)
            pos_idx = classes.index(1) if 1 in classes else -1
            y_scores = probas[:, pos_idx]
            y_pred = (y_scores >= 0.5).astype(int)
        except Exception:
            # Fallback if model predict_proba fails
            y_scores = np.zeros(len(test_observations))
            y_pred = np.zeros(len(test_observations), dtype=int)

        # Baseline predictions (deterministic formula)
        baseline_scores = []
        for o in test_observations:
            f = o.features
            b_score = (
                0.35 * (1.0 if f.is_direct_test_change or f.symbol_overlap_count > 0 else 0.0)
                + 0.25 * (1.0 if f.dependency_distance == 0 else max(0.0, 1.0 - 0.25 * f.dependency_distance))
                + 0.15 * f.requirement_priority_weight
                + 0.15 * min(1.0, f.blast_radius_depth / 3.0)
                + 0.10 * (f.historical_failure_rate if f.has_historical_data else 0.0)
            )
            baseline_scores.append(round(b_score, 4))
        baseline_scores = np.array(baseline_scores)
        baseline_pred = (baseline_scores >= 0.5).astype(int)

        # Calculate metrics
        precision = round(float(precision_score(y_true, y_pred, zero_division=0)), 4)
        recall = round(float(recall_score(y_true, y_pred, zero_division=0)), 4)
        f1 = round(float(f1_score(y_true, y_pred, zero_division=0)), 4)

        try:
            pr_auc = round(float(average_precision_score(y_true, y_scores)), 4)
        except Exception:
            pr_auc = None

        # Baseline metrics
        b_precision = round(float(precision_score(y_true, baseline_pred, zero_division=0)), 4)
        b_recall = round(float(recall_score(y_true, baseline_pred, zero_division=0)), 4)
        b_f1 = round(float(f1_score(y_true, baseline_pred, zero_division=0)), 4)

        # Top-K Fault Detection Recall
        # What % of all positive items (y_true == 1) are captured in top K ranked items?
        total_faults = int(np.sum(y_true == 1))
        effective_k = min(top_k, len(test_observations))

        model_rank_indices = np.argsort(-y_scores)[:effective_k]
        model_topk_faults = int(np.sum(y_true[model_rank_indices] == 1))
        model_topk_recall = round(model_topk_faults / total_faults, 4) if total_faults > 0 else 1.0

        base_rank_indices = np.argsort(-baseline_scores)[:effective_k]
        base_topk_faults = int(np.sum(y_true[base_rank_indices] == 1))
        base_topk_recall = round(base_topk_faults / total_faults, 4) if total_faults > 0 else 1.0

        return {
            "status": "evaluated",
            "sample_count": len(test_observations),
            "positive_count": total_faults,
            "negative_count": int(len(test_observations) - total_faults),
            "metrics": {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "pr_auc": pr_auc,
                f"top_{effective_k}_fault_recall": model_topk_recall,
            },
            "baseline_comparison": {
                "baseline_name": "deterministic_explainable_baseline",
                "precision": b_precision,
                "recall": b_recall,
                "f1_score": b_f1,
                f"top_{effective_k}_fault_recall": base_topk_recall,
                "model_improvement_f1": round(f1 - b_f1, 4),
            },
            "provenance": list(set(o.label_provenance for o in test_observations)),
            "contains_synthetic": any(o.is_synthetic for o in test_observations),
        }
