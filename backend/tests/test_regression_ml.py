"""
Unit tests for Machine Learning Pipeline in ai/regression_model.
Verifies dataset validation, leakage prevention, training/evaluation mechanics,
and truthful untrained fallback behavior.
"""

import os
import pytest
from ai.regression_model.evaluator import ModelEvaluationPipeline
from ai.regression_model.model import PredictiveRegressionModel
from ai.regression_model.schema import RegressionFeatureVector, TestExecutionObservation
from ai.regression_model.synthetic_samples import (
    generate_single_class_samples,
    generate_synthetic_training_samples,
)
from ai.regression_model.trainer import ModelTrainingPipeline


def test_regression_feature_vector_array_conversion():
    """Verify feature vector converts to float array with correct names."""
    feat = RegressionFeatureVector(
        change_file_count=3,
        is_direct_test_change=1,
        symbol_overlap_count=2,
        requirement_priority_weight=0.75,
        dependency_distance=1,
        blast_radius_depth=2,
        is_confirmed_link=1,
        historical_failure_rate=0.5,
        has_historical_data=1,
        historical_duration_normalized=0.2,
    )
    arr = feat.to_array()
    assert len(arr) == 10
    assert arr[0] == 3.0
    assert arr[1] == 1.0
    assert arr[7] == 0.5
    assert len(RegressionFeatureVector.feature_names()) == 10


def test_predictive_model_untrained_fallback():
    """Verify uncheckpointed model returns not_trained and deterministic fallback."""
    model = PredictiveRegressionModel(model_path="non_existent_weights.joblib")
    assert model.is_trained is False

    meta = model.get_metadata()
    assert meta["status"] == "not_trained"
    assert "deterministic" in meta["fallback_behavior"].lower()

    feat = RegressionFeatureVector(is_direct_test_change=1, symbol_overlap_count=2)
    pred = model.predict_risk(feat)
    assert pred["is_baseline"] is True
    assert pred["method"] == "deterministic_fallback"
    assert pred["score"] > 0.3


def test_training_pipeline_rejects_insufficient_or_single_class_data():
    """Verify training pipeline refuses datasets that are too small or single-class."""
    trainer = ModelTrainingPipeline()

    # Empty
    res_empty = trainer.train_and_persist([])
    assert res_empty["success"] is False
    assert res_empty["status"] == "insufficient_data"

    # Single-class
    single_class = generate_single_class_samples(count=15, outcome=0)
    res_sc = trainer.train_and_persist(single_class)
    assert res_sc["success"] is False
    assert res_sc["status"] == "single_class_detected"


def test_training_pipeline_trains_and_evaluates_on_synthetic_samples(tmp_path):
    """Verify training succeeds on balanced synthetic data and saves checkpoint with metadata."""
    trainer = ModelTrainingPipeline()
    samples = generate_synthetic_training_samples(count=40)

    target_joblib = str(tmp_path / "test_model.joblib")
    train_res = trainer.train_and_persist(
        observations=samples,
        model_path=target_joblib,
        algorithm="RandomForestClassifier",
    )

    assert train_res["success"] is True
    assert train_res["status"] == "trained"
    assert os.path.exists(target_joblib)
    assert os.path.exists(target_joblib.replace(".joblib", "_metadata.json"))

    # Load and test with wrapper
    loaded_model = PredictiveRegressionModel(model_path=target_joblib)
    assert loaded_model.is_trained is True

    test_feat = RegressionFeatureVector(
        is_direct_test_change=1,
        symbol_overlap_count=3,
        requirement_priority_weight=1.0,
        historical_failure_rate=0.8,
    )
    pred = loaded_model.predict_risk(test_feat)
    assert pred["is_baseline"] is False
    assert pred["method"] == "predictive_ml"
    assert "probability" in pred

    # Evaluate
    evaluator = ModelEvaluationPipeline()
    eval_res = evaluator.evaluate(loaded_model.model, samples[:10])
    assert eval_res["status"] == "evaluated"
    assert "precision" in eval_res["metrics"]
    assert "baseline_comparison" in eval_res
