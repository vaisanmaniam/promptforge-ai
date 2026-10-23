# PromptForge AI: Dataset Governance & Model Evaluation

## 1. Dataset Architecture & Governance

The PromptForge AI dataset repository resides in `ai/datasets/` and provides structured, schema-validated software engineering prompt data for training and evaluating local AI models.

### 1.1 Schema Definition (`PromptDatasetExample`)
Every prompt record is validated against a Pydantic schema:
* **`example_id`**: Stable unique identifier (e.g. `PFE-0001` through `PFE-0120`).
* **`prompt`**: Full text of the software engineering request.
* **`task_category`**: One of 8 supported categories.
* **`components_present`**: Explicitly detected components.
* **`missing_information`**: Gaps in context, technology, or constraints.
* **`ambiguity_labels`**: Identified ambiguous or open-ended phrases.
* **`reference_quality`**: Ground-truth sub-scores (clarity, context, specificity, constraints, output, completeness, overall).
* **`metadata`**: Provenance (`curated_seed`, `synthetic`, `reviewed_human`), split (`train`, `val`, `test`), and group identifier (`group_id`).

---

## 2. Seed Dataset Distribution

The seed dataset (`ai/datasets/seed_prompts.json`) contains **120 curated examples**:

### Class Balance (15 examples per category)
- `code_generation`: 15
- `debugging`: 15
- `code_review`: 15
- `api_development`: 15
- `sql_generation`: 15
- `test_generation`: 15
- `documentation`: 15
- `devops`: 15

### Split Distribution (Group-Aware Partitioning)
- **Train split**: 80 examples (66.7%)
- **Validation split**: 16 examples (13.3%)
- **Test split**: 24 examples (20.0%)

### Leakage Safeguards
The validator (`ai/datasets/validator.py`) enforces:
1. **Normalized String Deduplication**: Prevents identical prompt texts across different splits.
2. **Group ID Isolation**: Prompts sharing the same `group_id` cannot be split across train and test.

---

## 3. Classifier Training & Evaluation Results

### 3.1 Training Execution
Execute offline training via:
```bash
python -m ai.training.train_classifier
```

### 3.2 Actual Computed Evaluation Metrics (Test Split: 24 samples)

| Model / Baseline | Accuracy | Macro F1 | Performance Delta |
| :--- | :--- | :--- | :--- |
| **Majority-Class Dummy Baseline** | **12.5%** | **0.0278** | Baseline |
| **Rule-Based Heuristic Baseline** | **58.3%** | **0.5833** | +45.8% Acc |
| **TF-IDF + Logistic Regression (ML Model)** | **83.3%** | **0.8405** | **+70.8% Acc vs Dummy** |

Evaluation reports and metadata are logged to:
- `ai/models/prompt_classifier_v1_metadata.json`
- `ai/evaluation/evaluation_report.json`

---

## 4. Dataset Expansion Guidelines

To contribute new examples to the dataset:
1. Ensure the prompt represents a genuine software engineering request.
2. Label present components, missing information, and ambiguity markers.
3. Assign a unique `group_id` if generating related variations to prevent split leakage.
4. Run validation:
   ```bash
   python -m ai.datasets.validator ai/datasets/seed_prompts.json
   ```
5. Flag any synthetic examples explicitly using `is_synthetic: true`.
