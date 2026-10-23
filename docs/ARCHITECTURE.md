# PromptForge AI: System Architecture

## 1. Architectural Vision & Core Principles

PromptForge AI is an intelligent prompt-to-software engineering platform engineered around a core tenet: **model predictions must never be conflated with deterministic verification results**.

Commercial AI code generators often produce hallucinations, silent security bugs, and unverified assumptions. PromptForge AI addresses this through:
1. **Schema-Enforced Requirement Extraction**: Natural language prompts are translated into structured, validated requirement objects with unique identifiers and explicit acceptance criteria.
2. **Bidirectional Requirement Traceability**: Directed acyclic graphs (DAGs) link requirements directly to code elements (functions, classes) and verification tests.
3. **Local-First & Open-Weights AI**: No dependency on paid third-party APIs (OpenAI, Claude, Gemini). All model execution runs locally via open weights (e.g., Ollama / llama.cpp).
4. **Predictive Regression Intelligence**: Machine learning models (LightGBM/XGBoost) estimate test failure probability based on code diffs and test history to prioritize test runs.
5. **Isolated Execution Sandbox**: Untrusted generated code is strictly barred from the host API process and executed inside constrained Docker containers with network access disabled.
6. **Evidence-Guided Repair**: Failing test assertions, tracebacks, and static analysis findings form structured feedback loops for targeted, budget-bounded repair attempts.

---

## 2. High-Level System Architecture

```
+-----------------------------------------------------------------------------------+
|                                 FRONTEND CONSOLE                                  |
|   React 18 + TypeScript + Vite + Tailwind CSS (Developer Tool Design System)     |
|   Dashboard | Prompt Intelligence | Requirement Graph | Verification | Model Lab   |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST (VITE_API_BASE_URL)
                                           v
+-----------------------------------------------------------------------------------+
|                              BACKEND API GATEWAY                                  |
|                 FastAPI (Python 3.11) + Uvicorn + Pydantic v2                     |
|                                                                                   |
|  [/health]                     [/system/status]                [/api/v1/...]      |
|  Liveness Probe (Decoupled)    Deep Telemetry & Diagnostics   Core Subsystems     |
+-------------------+----------------------+--------------------+-------------------+
                    |                      |                    |
         +----------v---------+  +---------v----------+  +------v-------+
         |  PostgreSQL 16     |  | Local AI Runtime   |  | Docker Host  |
         |  (SQLAlchemy +     |  | (Ollama / GGUF)    |  | Sandbox      |
         |   asyncpg)         |  | Qwen2.5-Coder:1.5b |  | Isolated Run |
         +--------------------+  +--------------------+  +--------------+
```

---

## 3. Subsystem Breakdown & Responsibilities

### 3.1 Backend Application Layer (`backend/app/`)
* **`core/`**: Configuration management using `pydantic-settings`, structured logging, and application lifecycle events.
* **`api/v1/`**: Versioned REST API routers:
  - `/health`: Decoupled liveness probe.
  - `/system/status`: Subsystem readiness telemetry.
  - `/prompts/analyze`: Multi-label classification, component gap detection, and quality scoring.
  - `/prompts/optimize`: Intent-preserving prompt optimization and token efficiency.
  - `/requirements/`: Requirement extraction, validation, persistence, NetworkX graph traversal, and blast-radius impact analysis.
  - `/verification/`: Code artifact ingestion, requirement-to-code traceability linking, and Docker-isolated test verification.
  - `/regression/`: Change impact analysis, deterministic & ML test prioritization, budget-based selection, and historical observation telemetry.
  - `/repair/`: Failure analysis diagnosis, candidate repair proposal generation, explicit approval/rejection lifecycle, patch application, Docker verification, snapshot rollback, and audit trail.
* **`db/`**: Asynchronous SQLAlchemy 2.0 session factory with connection pooling and health checks.
* **`models/`**: Relational tables for specifications, requirement items, ingested projects, code artifacts, traceability links, verification runs, change analyses, test execution history, failure diagnoses, repair proposals, and repair audit events (`requirement.py`, `verification.py`, `regression.py`, `repair.py`).
* **`services/diagnostics.py`**: Subsystem telemetry engine inspecting PostgreSQL, Ollama, model checkpoints, and Docker sandbox.
* **`services/prompt_intelligence/`**: Component detection, ambiguity analysis, deterministic scoring, optimization, and BPE token counting.
* **`services/requirement_intelligence/`**: Deterministic requirement extractor, validation heuristics, NetworkX directed graph engine, truthful coverage calculator, and resilient storage repository with local fallback.
* **`services/verification/`**: Safe archive ingestion, SHA-256 fingerprinting, AST symbol extraction, deterministic code and test traceability linking, fail-closed Docker runner, and requirement evidence verdicts.
* **`services/regression/`**: Structural change impact analysis, explainable deterministic prioritizer, test selection with top-k and budget bounds, and test execution history collector with JSON fallback.
* **`services/repair/`**: Failure analysis parser, multi-tier deterministic and local model candidate generator, workspace jail and hash integrity patcher, immutable snapshot rollback, and lifecycle approval coordinator with hybrid SQL/JSON storage.

### 3.2 AI Subsystem (`ai/`)
* **`datasets/`**: Schema-validated dataset infrastructure (`schema.py`, `validator.py`, `seed_prompts.json` with 120 curated software engineering prompts across 8 task categories).
* **`prompt_classifier/`**: Pluggable classifier interface (`BasePromptClassifier`), rule-based keyword/regex baseline (`RuleBasedClassifier`), and trained TF-IDF + Logistic Regression model (`SklearnPromptClassifier`).
* **`training/`**: Reproducible offline training pipeline (`train_classifier.py`) outputting `ai/models/prompt_classifier_v1.joblib` and metrics metadata.
* **`evaluation/`**: Deterministic benchmark pipeline (`evaluate_classifier.py`) generating `evaluation_report.json` comparing ML model vs baselines.
* **`requirement_intelligence/`**: Deterministic and explainable requirement extraction engine with explicit vs. inferred categorization and assumption linking (Phase 3).
* **`code_model/`**: Provider-independent model abstraction connecting to local Ollama / OpenAI-compatible endpoints (Phase 4).
* **`regression_model/`**: Predictive ML regression testing pipeline (`schema.py`, `model.py`, `trainer.py`, `evaluator.py`, `synthetic_samples.py`) predicting test failure probabilities with change-level leakage prevention, Top-k fault detection recall, and baseline benchmarking (Phase 5).

### 3.3 Execution Sandbox (`sandbox/`)
* **`runners/`**: Ephemeral runner scripts executing generated code within isolated Docker containers.
* **`security_policies/`**: Seccomp profiles, non-root user execution, memory caps (512MB), CPU quotas (1 core), execution timeouts (10s), and zero network egress (`--network none`).

### 3.4 Frontend Developer Console (`frontend/`)
* Built with React 18, TypeScript, Vite, Tailwind CSS, and React Router.
* Uses a dark navy/charcoal developer palette (`#0B0F17`, `#111827`, `#1E293B`) with cyan and violet accents.
* Strictly displays live backend telemetry. Unimplemented modules are explicitly tagged with their respective roadmap phases.

---

## 4. Data Flow: Prompt to Verified Software

```
1. Natural Language Prompt
         |
         v
2. Prompt Intelligence Engine -----> Ambiguity / Missing Info Detected?
         |                                 | (Yes) -> Return clarifying questions
         v (Complete)                      v (No)
3. Requirement Extractor
         |
         v
4. Requirement Traceability DAG (NetworkX)
         |
         v
5. Local Code Model (Qwen2.5-Coder)
         |
         v
6. Isolated Execution Sandbox (Docker Container)
         |
         +-----> Tests Passed? ----+
         | (No)                    | (Yes)
         v                         v
7. Evidence-Guided Repair    8. Static Security Audit (Semgrep)
   (Traceback + Budget)            |
                                   v
                             9. Verified Software + Traceability Report
```

---

## 5. Security Architecture & Threat Boundaries

| Threat Vector | Mitigation Strategy | Enforced In |
| :--- | :--- | :--- |
| Malicious / Remote Code Execution | Generated code is never run in the API host process. Docker isolation with `--network none`, non-root user, and ephemeral mounts. | Sandbox Subsystem |
| Secret Leakage | `.env` variables filtered; DB passwords and stack traces stripped from API responses. | Backend Core & Middleware |
| Denial of Service (Infinite Loops) | Strict process execution timeouts (default 10s) enforced at OS/container level. | Sandbox Runner |
| Fabricated Verification / AI Hallucination | Model assertions are never treated as verification. Tests must execute and return exit code 0. | Verification Engine |
| Unauthorized Host Filesystem Access | Host directories are never mounted into sandbox containers; ephemeral `/tmp` only. | Docker Compose & Sandbox |

---

## 6. Local-First AI Runtime Abstraction

PromptForge AI defines a provider-independent AI interface:
- **Default Local Backend**: Ollama server (`http://localhost:11434`) running open-weight models (e.g. `qwen2.5-coder:1.5b` or `qwen2.5-coder:3b`).
- **Compatibility**: Any OpenAI-compatible local endpoint (e.g., `llama.cpp` server, `vLLM`, `LocalAI`).
- **No External Dependency**: The system contains zero integration with paid APIs (OpenAI, Anthropic, Google Gemini).
- **Graceful Diagnostics**: If Ollama is offline or the target model is not pulled, the system status endpoint reports `unavailable` with actionable terminal commands.
