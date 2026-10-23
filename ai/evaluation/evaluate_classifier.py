import datetime
import json
import os
import sys
from typing import Any, Dict
import joblib
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from ai.datasets.validator import validate_dataset_file
from ai.prompt_classifier.rules import RuleBasedClassifier


def evaluate_classifier_pipeline(
    model_path: str = "ai/models/prompt_classifier_v1.joblib",
    dataset_path: str = "ai/datasets/seed_prompts.json",
    report_output_path: str = "ai/evaluation/evaluation_report.json",
) -> Dict[str, Any]:
    """
    Evaluates trained model against the test split, compares against the
    rule-based baseline, and saves a comprehensive evaluation report.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model checkpoint not found: {model_path}. Train the model first.")

    pipeline = joblib.load(model_path)
    examples, stats = validate_dataset_file(dataset_path)

    test_examples = [e for e in examples if e.metadata.split == "test"]
    X_test = [e.prompt for e in test_examples]
    y_test = [e.task_category.value for e in test_examples]
    labels = sorted(list(set(y_test)))

    # Evaluate ML Model
    ml_preds = pipeline.predict(X_test)
    ml_acc = accuracy_score(y_test, ml_preds)
    ml_macro_f1 = f1_score(y_test, ml_preds, average="macro", zero_division=0)
    ml_report = classification_report(y_test, ml_preds, labels=labels, output_dict=True, zero_division=0)
    ml_cm = confusion_matrix(y_test, ml_preds, labels=labels).tolist()

    # Evaluate Rule-based Baseline
    rule_classifier = RuleBasedClassifier()
    rule_preds = [rule_classifier.predict(x).predicted_category for x in X_test]
    rule_acc = accuracy_score(y_test, rule_preds)
    rule_macro_f1 = f1_score(y_test, rule_preds, average="macro", zero_division=0)

    report = {
        "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model_artifact": model_path,
        "dataset_path": dataset_path,
        "test_sample_count": len(X_test),
        "classes": labels,
        "ml_model_performance": {
            "accuracy": round(float(ml_acc), 4),
            "macro_f1": round(float(ml_macro_f1), 4),
            "classification_report": ml_report,
            "confusion_matrix": ml_cm,
        },
        "baseline_comparison": {
            "rule_based_accuracy": round(float(rule_acc), 4),
            "rule_based_macro_f1": round(float(rule_macro_f1), 4),
            "ml_vs_rules_accuracy_delta": round(float(ml_acc - rule_acc), 4),
            "ml_vs_rules_macro_f1_delta": round(float(ml_macro_f1 - rule_macro_f1), 4),
        },
    }

    os.makedirs(os.path.dirname(report_output_path), exist_ok=True)
    with open(report_output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Evaluation complete. ML Accuracy: {ml_acc * 100:.1f}%, Rule Accuracy: {rule_acc * 100:.1f}%")
    print(f"Report saved to: {report_output_path}")

    return report


if __name__ == "__main__":
    evaluate_classifier_pipeline()
