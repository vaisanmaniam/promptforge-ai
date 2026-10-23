import json
import os
from collections import Counter
from typing import Any, Dict, List, Set, Tuple
from ai.datasets.schema import PromptDatasetExample, TaskCategory


class DatasetValidationError(Exception):
    """Raised when a dataset fails schema, balance, or integrity checks."""
    pass


class LeakageError(DatasetValidationError):
    """Raised when data leakage between train/val/test splits is detected."""
    pass


def validate_dataset_records(records: List[Dict[str, Any]]) -> Tuple[List[PromptDatasetExample], Dict[str, Any]]:
    """
    Validates a list of dictionary records against PromptDatasetExample schema,
    enforcing uniqueness, split integrity, and leakage prevention.
    """
    validated_examples: List[PromptDatasetExample] = []
    seen_ids: Set[str] = set()
    split_prompts: Dict[str, Set[str]] = {"train": set(), "val": set(), "test": set()}
    group_split_map: Dict[str, str] = {}
    class_counts = Counter()
    split_counts = Counter()

    for idx, raw in enumerate(records):
        try:
            example = PromptDatasetExample.model_validate(raw)
        except Exception as err:
            raise DatasetValidationError(f"Record at index {idx} failed schema validation: {err}")

        # Unique ID check
        if example.example_id in seen_ids:
            raise DatasetValidationError(f"Duplicate example_id detected: {example.example_id}")
        seen_ids.add(example.example_id)

        # Leakage check 1: Exact text across splits
        normalized_text = " ".join(example.prompt.strip().lower().split())
        current_split = example.metadata.split
        for other_split, prompt_set in split_prompts.items():
            if other_split != current_split and normalized_text in prompt_set:
                raise LeakageError(
                    f"Train/test leakage: Prompt '{example.prompt[:40]}...' in {current_split} "
                    f"also exists in {other_split} split."
                )
        split_prompts[current_split].add(normalized_text)

        # Leakage check 2: Same group_id cannot cross splits
        group_id = example.metadata.group_id
        if group_id in group_split_map and group_split_map[group_id] != current_split:
            raise LeakageError(
                f"Group leakage: Group '{group_id}' assigned to both "
                f"{group_split_map[group_id]} and {current_split}."
            )
        group_split_map[group_id] = current_split

        class_counts[example.task_category.value] += 1
        split_counts[current_split] += 1
        validated_examples.append(example)

    # Verification: all 8 task categories must be represented
    all_categories = {c.value for c in TaskCategory}
    missing_categories = all_categories - set(class_counts.keys())
    if missing_categories:
        raise DatasetValidationError(f"Dataset missing examples for categories: {missing_categories}")

    stats = {
        "total_examples": len(validated_examples),
        "split_distribution": dict(split_counts),
        "class_distribution": dict(class_counts),
        "synthetic_count": sum(1 for e in validated_examples if e.metadata.is_synthetic),
        "curated_count": sum(1 for e in validated_examples if not e.metadata.is_synthetic),
    }

    return validated_examples, stats


def validate_dataset_file(filepath: str) -> Tuple[List[PromptDatasetExample], Dict[str, Any]]:
    """Loads a JSON dataset file and runs complete integrity verification."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise DatasetValidationError("Dataset file root must be a JSON array of examples.")

    return validate_dataset_records(data)


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "ai/datasets/seed_prompts.json"
    try:
        examples, summary = validate_dataset_file(target)
        print(f"Validation successful! Total examples: {summary['total_examples']}")
        print(f"Splits: {summary['split_distribution']}")
        print(f"Classes: {summary['class_distribution']}")
    except Exception as exc:
        print(f"Dataset validation failed: {exc}")
        sys.exit(1)
