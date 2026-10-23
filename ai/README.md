# AI Subsystem Architecture Scaffolding

This directory contains the machine learning pipelines, dataset schemas, training scripts, evaluation harnesses, and model export utilities for PromptForge AI.

## Subdirectories

- **`datasets/`**: Curated, versioned dataset manifests (prompt classification, requirement extraction, regression testing logs).
- **`prompt_classifier/`**: Lightweight encoder-based classifier and deterministic heuristics for task classification and missing information detection.
- **`requirement_extractor/`**: Supervised instruction-tuning and few-shot schemas for extracting verifiable requirements from prompts.
- **`code_model/`**: Provider-independent abstraction and prompt templates for local open-weight code models (e.g., Qwen2.5-Coder, DeepSeek-Coder).
- **`risk_predictor/`**: Tabular ML models (LightGBM / scikit-learn) for predicting regression-test failure risk from code diffs and test history.
- **`training/`**: Reproducible training pipelines, dataset splitters, and MLflow run scripts.
- **`evaluation/`**: Deterministic benchmark runners, test-suite evaluation, and metric computation.
- **`models/`**: Local model weights directory (ignored in version control, verified by system diagnostic check).
