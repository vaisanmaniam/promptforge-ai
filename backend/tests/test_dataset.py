import os
import pytest
from ai.datasets.schema import PromptDatasetExample, TaskCategory
from ai.datasets.validator import (
    DatasetValidationError,
    LeakageError,
    validate_dataset_file,
    validate_dataset_records,
)


def test_seed_dataset_validation():
    """Verify seed_prompts.json conforms to all schema, balance, and split rules."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    dataset_path = os.path.join(root_dir, "ai", "datasets", "seed_prompts.json")
    if not os.path.exists(dataset_path):
        pytest.fail(f"Seed dataset missing at {dataset_path}")

    examples, stats = validate_dataset_file(dataset_path)
    assert len(examples) == 120
    assert stats["total_examples"] == 120

    # Ensure all 8 categories are represented with at least 10 examples each
    for cat in TaskCategory:
        assert stats["class_distribution"][cat.value] >= 10

    # Ensure train, val, and test splits are present
    assert stats["split_distribution"]["train"] >= 60
    assert stats["split_distribution"]["val"] >= 10
    assert stats["split_distribution"]["test"] >= 15


def test_duplicate_id_detection():
    """Ensure duplicate example_id raises DatasetValidationError."""
    bad_records = [
        {
            "example_id": "PFE-DUP-1",
            "prompt": "First prompt to implement quicksort.",
            "task_category": "code_generation",
            "components_present": ["objective"],
            "missing_information": [],
            "ambiguity_labels": [],
            "reference_quality": {
                "clarity": 80.0, "context": 50.0, "specificity": 80.0,
                "constraints": 50.0, "output_definition": 50.0, "completeness": 60.0, "overall_score": 62.0
            },
            "metadata": {"source": "synthetic", "split": "train", "is_synthetic": True, "group_id": "g1", "created_at": "2026-10-09T00:00:00Z"}
        },
        {
            "example_id": "PFE-DUP-1",  # duplicate ID
            "prompt": "Second prompt to implement mergesort.",
            "task_category": "code_generation",
            "components_present": ["objective"],
            "missing_information": [],
            "ambiguity_labels": [],
            "reference_quality": {
                "clarity": 80.0, "context": 50.0, "specificity": 80.0,
                "constraints": 50.0, "output_definition": 50.0, "completeness": 60.0, "overall_score": 62.0
            },
            "metadata": {"source": "synthetic", "split": "train", "is_synthetic": True, "group_id": "g2", "created_at": "2026-10-09T00:00:00Z"}
        }
    ]

    with pytest.raises(DatasetValidationError, match="Duplicate example_id"):
        validate_dataset_records(bad_records)


def test_split_leakage_detection():
    """Ensure identical prompt crossing from train to test raises LeakageError."""
    leaky_records = [
        {
            "example_id": "PFE-LEAK-1",
            "prompt": "Identical prompt text for sorting integers.",
            "task_category": "code_generation",
            "components_present": ["objective"],
            "missing_information": [],
            "ambiguity_labels": [],
            "reference_quality": {
                "clarity": 80.0, "context": 50.0, "specificity": 80.0,
                "constraints": 50.0, "output_definition": 50.0, "completeness": 60.0, "overall_score": 62.0
            },
            "metadata": {"source": "synthetic", "split": "train", "is_synthetic": True, "group_id": "g1", "created_at": "2026-10-09T00:00:00Z"}
        },
        {
            "example_id": "PFE-LEAK-2",
            "prompt": "Identical prompt text for sorting integers.",  # exact leak across split
            "task_category": "code_generation",
            "components_present": ["objective"],
            "missing_information": [],
            "ambiguity_labels": [],
            "reference_quality": {
                "clarity": 80.0, "context": 50.0, "specificity": 80.0,
                "constraints": 50.0, "output_definition": 50.0, "completeness": 60.0, "overall_score": 62.0
            },
            "metadata": {"source": "synthetic", "split": "test", "is_synthetic": True, "group_id": "g2", "created_at": "2026-10-09T00:00:00Z"}
        }
    ]

    with pytest.raises(LeakageError, match="Train/test leakage"):
        validate_dataset_records(leaky_records)
