# PromptForge AI: AI & ML Development Plan

## 1. Executive Summary & Hardware Feasibility

PromptForge AI develops an autonomous, local-first artificial intelligence capability tailored for software engineering tasks.

### 1.1 Target Hardware Constraints
Based on host diagnostic telemetry (Windows 11, Intel Core i5-1335U 10-core CPU, 16 GB RAM with ~3.8 GB free, and integrated Intel Iris Xe Graphics without a dedicated NVIDIA CUDA GPU):
1. **Foundation Pretraining from Scratch**: Out of scope. Training a multi-billion parameter foundation code LLM from scratch requires hundreds of GPU cluster hours and terabytes of curated code tokens.
2. **Local Code Inference**: Fully feasible using quantized open-weight code models (GGUF 4-bit / 8-bit quantized models such as `qwen2.5-coder:1.5b-instruct-q4_K_M` or `deepseek-coder:1.3b-instruct`) executed on CPU via Ollama or llama.cpp.
3. **Prompt Classification & Missing Information Detection**: Highly suitable for distilled transformer encoders (e.g. `all-MiniLM-L6-v2`, `deberta-v3-small`) or classical TF-IDF/scikit-learn classifiers running in milliseconds on CPU.
4. **Predictive Regression Risk Estimation**: Executed via gradient boosted decision trees (`LightGBM` / `XGBoost`), achieving sub-second training and inference on CPU while outperforming complex deep networks on tabular diff metrics.

---

## 2. Model Architecture & Selection
 
| Task Component | Model Family | Parameters | Runtime Engine | Execution Target | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Prompt Classifier** | TF-IDF + Logistic Regression | ~2,500 Features | scikit-learn (CPU) | CPU (Milliseconds) | **Trained & Evaluated (Phase 2)** |
| **Rule Baseline** | Heuristic Regex Matcher | N/A | Python Regex | CPU (Sub-millisecond) | **Implemented (Phase 2)** |
| **Component Detector**| Pattern + Heuristic | N/A | Python Rules | CPU (Sub-millisecond) | **Implemented (Phase 2)** |
| **Ambiguity Detector**| Subjective Pattern Rules | N/A | Python Rules | CPU (Sub-millisecond) | **Implemented (Phase 2)** |
| **Quality Scorer** | Deterministic 6-Dimension | N/A | Configured Weights | CPU (Sub-millisecond) | **Implemented (Phase 2)** |
| **Prompt Optimizer** | Template Injection + Assumptions | N/A | Python Rules | CPU (Sub-millisecond) | **Implemented (Phase 2)** |
| **Requirement Extractor** | Qwen2.5-Coder / Mistral-7B LoRA | 1.5B - 7B | Ollama / vLLM | CPU (1.5B) / GPU (7B) | Planned (Phase 3) |
| **Code Gen & Repair**| Qwen2.5-Coder-Instruct | 1.5B (GGUF Q4) | Ollama | CPU | Planned (Phase 4) |
| **Regression Risk** | LightGBM / XGBoost | Tabular GBDT | scikit-learn / LightGBM | CPU | Planned (Phase 5) |

### 2.1 Prompt Classifier Evaluation Summary (Phase 2 Benchmarks)
- **Training Samples**: 96 (80 train, 16 val) across 8 balanced categories.
- **Test Samples**: 24 held-out evaluation samples (zero train/test leakage).
- **Majority-Class Baseline Accuracy**: **12.5%** (Macro F1: 0.0278)
- **Rule-Based Baseline Accuracy**: **58.3%** (Macro F1: 0.5833)
- **Trained Sklearn Classifier Accuracy**: **83.3%** (Macro F1: **0.8405**)
- **Improvement over Majority**: **+70.8% accuracy**
- **Improvement over Heuristic Rules**: **+25.0% accuracy**

---

## 3. Dataset Curation & Provenance

### 3.1 Prompt Classification & Ambiguity Dataset
* **Source**: Curated software engineering prompt benchmarks (e.g., CodeSearchNet prompt samples, GitHub issues, StackOverflow prompts) annotated across 8 categories:
  - Code Generation, Debugging, Code Review, API Development, SQL Generation, Test Generation, Documentation, DevOps.
* **Ambiguity Annotations**: Prompts scored for missing requirements (e.g., missing input/output types, missing technology stack, missing error handling criteria).
* **Splits**: 70% Train, 15% Validation, 15% Test with deterministic random seeds and SHA-256 data split hashing.

### 3.2 Regression Risk & Test Failure Dataset
* **Source**: Git commit history and automated test run logs extracted from open-source repositories.
* **Features**:
  - Churn (lines added, deleted)
  - Cyclomatic complexity delta
  - Changed AST node types (function signature, control flow, imports)
  - Historical test failure frequency
  - Test suite distance (Levenshtein path distance between modified file and test file)
* **Target Label**: Binary test failure (`0` = pass, `1` = fail).

---

## 4. Training & Fine-Tuning Strategy

### 4.1 Classical ML & Encoders (Local Training)
* LightGBM and scikit-learn models are trained locally in minutes.
* Experiments logged to **MLflow** tracking:
  - AUC-ROC, Precision-Recall AUC
  - Average Percentage of Faults Detected (APFD) for test prioritization
  - Inference latency per commit diff

### 4.2 Supervised Fine-Tuning (PEFT/LoRA) for Requirement Extraction
* Instruction-tuning format:
  ```json
  {
    "instruction": "Extract schema-validated requirements from the prompt.",
    "input": "Build a FastAPI endpoint that accepts user signup and hashes passwords with bcrypt.",
    "output": {
      "requirements": [
        {
          "id": "REQ-001",
          "category": "functional",
          "description": "Expose POST /signup endpoint",
          "acceptance_criteria": "Accepts email and password; returns 201 Created."
        },
        {
          "id": "REQ-002",
          "category": "security",
          "description": "Hash passwords with bcrypt",
          "acceptance_criteria": "No plain text stored; bcrypt work factor >= 12."
        }
      ]
    }
  }
  ```
* Fine-tuning executed using LoRA (Low-Rank Adaptation, rank=16, alpha=32) with 4-bit quantization (QLoRA) on cloud GPU (e.g., Google Colab / Kaggle T4/A100) and exported as quantized GGUF weights for local inference.

---

## 5. Evaluation Methodology & Metrics

1. **Requirement Extraction**:
   - Schema Validity Rate: % of outputs conforming strictly to Pydantic schema.
   - Requirement Recall: % of ground-truth functional and non-functional requirements captured.
2. **Code Generation & Verification**:
   - pass@1 and pass@k against unit test suites.
   - Semgrep zero-vulnerability rate.
3. **Regression Intelligence**:
   - APFD (Average Percentage of Faults Detected) comparing ML-weighted order vs random order vs execution time.
   - Reduction in time-to-first-failure detection.

---

## 6. Open-Weight Licensing & Compliance

* **Qwen2.5-Coder**: Apache 2.0 license (permissive commercial & academic use).
* **DeepSeek-Coder**: DeepSeek license (open weights, academic research).
* **Sentence-Transformers**: Apache 2.0 license.
* **LightGBM / XGBoost**: MIT / Apache 2.0 licenses.
All models utilized have verifiable open-source provenance and require zero proprietary cloud API subscriptions.
