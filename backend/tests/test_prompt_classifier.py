import os
import pytest
from ai.prompt_classifier.model import SklearnPromptClassifier
from ai.prompt_classifier.rules import RuleBasedClassifier


def test_rule_based_classifier_predictions():
    """Verify rule-based classifier handles core tasks."""
    classifier = RuleBasedClassifier()

    sql_res = classifier.predict("SELECT u.id, u.email FROM users u WHERE u.active = true")
    assert sql_res.predicted_category == "sql_generation"
    assert sql_res.is_baseline is True

    test_res = classifier.predict("Write pytest unit tests asserting calculate_discount with mocks")
    assert test_res.predicted_category == "test_generation"

    devops_res = classifier.predict("Write a multi-stage Dockerfile for FastAPI deployment on Kubernetes")
    assert devops_res.predicted_category == "devops"


def test_trained_sklearn_classifier_predictions():
    """Verify trained scikit-learn model outputs valid predictions, confidence, and metadata."""
    classifier = SklearnPromptClassifier()
    assert classifier.is_trained is True

    prompt = "Write a PostgreSQL query with window function DENSE_RANK to rank salaries"
    res = classifier.predict(prompt)

    assert res.predicted_category == "sql_generation"
    assert res.confidence > 0.2
    assert res.method == "ml_model"
    assert res.is_baseline is False
    assert len(res.probabilities) == 8
    # Probabilities should sum to approximately 1.0
    assert abs(sum(res.probabilities.values()) - 1.0) < 0.01

    meta = classifier.get_metadata()
    assert meta["status"] == "trained"
    assert len(meta["classes"]) == 8


def test_sklearn_classifier_untrained_fallback():
    """Verify classifier falls back to rule-based baseline when checkpoint is missing."""
    classifier = SklearnPromptClassifier(model_path="non_existent_model_path.joblib")
    assert classifier.is_trained is False

    res = classifier.predict("Fix NullPointerException in Spring Boot controller")
    assert res.predicted_category == "debugging"
    assert res.method == "untrained_baseline"
    assert res.is_baseline is True

    meta = classifier.get_metadata()
    assert meta["status"] == "untrained"
