import datetime
import json
import os
import sys
from typing import Any, Dict
import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline

from ai.datasets.validator import validate_dataset_file


def train_prompt_classifier(
    dataset_path: str = "ai/datasets/seed_prompts.json",
    model_output_path: str = "ai/models/prompt_classifier_v1.joblib",
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Trains a TF-IDF + Logistic Regression text classification pipeline
    on the validated seed dataset, evaluates against a majority-class baseline,
    and serializes the trained model artifact.
    """
    print(f"Loading and validating dataset from: {dataset_path}")
    examples, stats = validate_dataset_file(dataset_path)

    # Partition by defined splits (group-aware splits already validated)
    train_examples = [e for e in examples if e.metadata.split in ("train", "val")]
    test_examples = [e for e in examples if e.metadata.split == "test"]

    if len(train_examples) < 16 or len(test_examples) < 8:
        raise ValueError(
            f"Insufficient data for reliable training: "
            f"{len(train_examples)} train/val samples, {len(test_examples)} test samples."
        )

    X_train = [e.prompt for e in train_examples]
    y_train = [e.task_category.value for e in train_examples]

    X_test = [e.prompt for e in test_examples]
    y_test = [e.task_category.value for e in test_examples]

    labels = sorted(list(set(y_train)))
    print(f"Training on {len(X_train)} samples across {len(labels)} categories. Testing on {len(X_test)} samples.")

    # 1. Majority-class Dummy Baseline
    dummy = DummyClassifier(strategy="most_frequent", random_state=random_seed)
    dummy.fit(X_train, y_train)
    dummy_preds = dummy.predict(X_test)
    dummy_acc = accuracy_score(y_test, dummy_preds)
    dummy_f1 = f1_score(y_test, dummy_preds, average="macro", zero_division=0)

    # 2. Train TF-IDF + Logistic Regression Pipeline
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=2500,
                    sublinear_tf=True,
                    lowercase=True,
                    token_pattern=r"(?u)\b\w+\b",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=1.5,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    # 3. Compute Metrics
    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    report_dict = classification_report(y_test, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=labels).tolist()

    # 4. Serialize Model Artifacts
    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    joblib.dump(pipeline, model_output_path)

    metadata = {
        "model_name": "prompt_classifier_v1",
        "version": "1.0.0",
        "algorithm": "TF-IDF + LogisticRegression",
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "random_seed": random_seed,
        "dataset_path": dataset_path,
        "dataset_stats": stats,
        "classes": labels,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics": {
            "test_accuracy": round(float(acc), 4),
            "test_macro_f1": round(float(macro_f1), 4),
            "test_weighted_f1": round(float(weighted_f1), 4),
            "classification_report": report_dict,
            "confusion_matrix": cm,
        },
        "baseline_comparison": {
            "dummy_majority_strategy": "most_frequent",
            "dummy_accuracy": round(float(dummy_acc), 4),
            "dummy_macro_f1": round(float(dummy_f1), 4),
            "accuracy_improvement": round(float(acc - dummy_acc), 4),
            "macro_f1_improvement": round(float(macro_f1 - dummy_f1), 4),
        },
    }

    meta_path = model_output_path.replace(".joblib", "_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("\n--- Training Results ---")
    print(f"Accuracy:  {acc * 100:.1f}% (Majority Baseline: {dummy_acc * 100:.1f}%)")
    print(f"Macro F1:  {macro_f1:.4f} (Majority Baseline: {dummy_f1:.4f})")
    print(f"Model saved to: {model_output_path}")
    print(f"Metadata saved to: {meta_path}")

    return metadata


if __name__ == "__main__":
    ds_path = sys.argv[1] if len(sys.argv) > 1 else "ai/datasets/seed_prompts.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "ai/models/prompt_classifier_v1.joblib"
    train_prompt_classifier(ds_path, out_path)
