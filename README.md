# PromptForge AI

> **From Natural Language to Verified Software**
>
> *An Intelligent Prompt-to-Software Engineering Platform with Requirement Traceability, Predictive Regression Testing, and Automated Verification.*

---

## 1. Product Overview

PromptForge AI is a modular software engineering platform engineered to bridge the gap between high-level natural language requests and production-grade, verifiable software systems.

Unlike generic prompt chatbots or thin LLM wrappers, PromptForge AI enforces strict verification boundaries:
- **No Fabricated Correctness**: Model predictions are never treated as verification. Code is only verified when tests pass and static analysis rules succeed.
- **Requirement Traceability**: Software requirements are schema-validated, given stable IDs, and bidirectionally linked to code and tests in a directed graph.
- **Predictive Regression Intelligence**: Changes are evaluated using machine learning (LightGBM) trained on commit diffs and test history to prioritize high-risk test execution.
- **Local-First AI Execution**: Operates independently of paid commercial AI APIs (OpenAI, Claude, Gemini) using local open-weight models (e.g., Qwen2.5-Coder via Ollama / llama.cpp).
- **Execution Sandbox**: Untrusted generated code is isolated in non-networked Docker execution containers with hard CPU, memory, and timeout caps.

---

## 2. Platform Architecture

PromptForge AI is organized as a clean, modular monorepo:

```
promptforge-ai/
├── backend/                  # FastAPI (Python 3.11) backend service
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (health, system diagnostics, future modules)
│   │   ├── core/            # Configuration (pydantic-settings) & structured logging
│   │   ├── db/              # SQLAlchemy 2.0 async engine & session management
│   │   ├── schemas/         # Pydantic v2 domain schemas and response models
│   │   └── services/        # Subsystem diagnostic telemetry & business logic
│   ├── tests/               # Backend automated pytest suite (unit & integration)
│   └── requirements.txt     # Pinned backend dependencies
├── frontend/                 # React 18 + TypeScript + Vite + Tailwind CSS console
│   ├── src/
│   │   ├── api/             # Axios client & system API hooks
│   │   ├── components/      # Reusable layout and diagnostic UI components
│   │   ├── pages/           # Dashboard and module placeholder views
│   │   └── tests/           # Vitest and React Testing Library test suite
│   └── package.json         # Pinned frontend dependencies
├── ai/                       # AI pipelines, datasets, models & evaluation
│   ├── datasets/            # Versioned dataset schemas & splits
│   ├── models/              # Local model weights directory (ignored in git)
│   ├── prompt_classifier/   # Intent & ambiguity detection models
│   ├── requirement_extractor/ # Supervised requirement extraction
│   ├── code_model/          # Local inference abstractions (Ollama / GGUF)
│   └── risk_predictor/      # Tabular regression risk estimation models
├── sandbox/                  # Isolated container execution runners & policies
├── docs/                     # System architecture, AI plan & implementation roadmap
│   ├── ARCHITECTURE.md
│   ├── AI_DEVELOPMENT_PLAN.md
│   └── IMPLEMENTATION_ROADMAP.md
├── docker-compose.yml        # PostgreSQL 16 database with healthcheck
├── .env.example              # Environment variables template
└── README.md
```

---

## 3. Prerequisites

Ensure the following tools are installed on your host system:

- **Python**: Version 3.11 (`python --version`)
- **Node.js & npm**: Node.js v18+ (tested on v24.13.0, npm 11.6.2)
- **Docker & Docker Compose**: Docker CLI v24+ (for running PostgreSQL and isolated sandbox)
- **Ollama** *(Optional for Phase 1)*: For local open-weight model inference (`https://ollama.com`)

---

## 4. Quickstart Installation

### Step 1: Clone and Configure Environment

```bash
git clone <repo-url> promptforge-ai
cd promptforge-ai

# Copy environment template
cp .env.example .env
cp frontend/.env.example frontend/.env
```

### Step 2: Initialize Backend Virtual Environment

```bash
# Navigate to backend directory
cd backend

# Create dedicated virtual environment using Python 3.11
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install pinned dependencies
pip install -r requirements.txt
cd ..
```

### Step 3: Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## 5. Running the Application

### 5.1 Start the PostgreSQL Database (Docker)

```bash
# Start PostgreSQL service in background
docker compose up -d postgres

# Verify container health
docker compose ps
```

### 5.2 Start the Backend API Server

```bash
# From backend/ with virtual environment activated:
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Base URL: `http://localhost:8000/api/v1`
- Swagger Interactive Documentation: `http://localhost:8000/docs`
- Health Probe: `http://localhost:8000/api/v1/health`
- System Diagnostics: `http://localhost:8000/api/v1/system/status`

### 5.3 Start the Frontend Developer Console

```bash
# In a new terminal window:
cd frontend
npm run dev
```

- Frontend Console: `http://localhost:5173`

### 5.4 Train and Evaluate the Prompt Classifier (Offline)

```bash
# Validate seed dataset integrity and leakage safeguards
python -m ai.datasets.validator

# Train TF-IDF + Logistic Regression classifier and compare against majority baseline
python -m ai.training.train_classifier

# Evaluate model artifact against test split and compare against rule-based baseline
python -m ai.evaluation.evaluate_classifier
```

---

## 6. Running Test Suites

### Backend Tests (pytest)

```bash
cd backend
.\.venv\Scripts\pytest.exe tests -v
```

*Note: The test suite includes 70 unit and integration tests (68 passing, 2 integration tests skipped when PostgreSQL/Docker Desktop are stopped) covering health probes, system status reporting, dataset validation, prompt classification, component detection, quality scoring, optimizer contracts, token counting, deterministic requirement extraction, validation heuristics, NetworkX directed graphs, impact analysis, coverage reporting, safe archive ingestion, code traceability linking, static AST inspection, test discovery, fail-closed Docker execution, change impact analysis, deterministic regression ranking, ML pipeline training/evaluation, test selection under budgets, failure diagnosis, deterministic patch synthesis, workspace jail validation, snapshot rollback, approval lifecycle, and FastAPI endpoints.*

### Frontend Tests (Vitest)

```bash
cd frontend
npm test
```

*Note: 16 frontend tests passing across 7 test suites with zero TypeScript errors on production build.*

### Frontend Production Build Check

```bash
cd frontend
npm run build
```

---

## 7. System Diagnostics & Subsystem Capabilities

PromptForge AI features decoupled diagnostics and intelligence modules:
* **`/api/v1/health`**: Independent liveness probe indicating whether the FastAPI process is alive.
* **`/api/v1/system/status`**: Detailed diagnostic telemetry inspecting PostgreSQL, AI runtime (Ollama), local model artifacts, and Docker sandbox availability.
* **`/api/v1/prompts/analyze`**: Real-time prompt classification, multi-label component detection, ambiguity scoring, and deterministic quality evaluation.
* **`/api/v1/prompts/optimize`**: Objective-preserving prompt restructuring with assumption disclosure and token efficiency analysis.
* **`/api/v1/requirements/extract`**: Deterministic requirement extraction, acceptance criteria generation, and explicit vs inferred status labeling.
* **`/api/v1/requirements/specifications`**: CRUD persistence of requirement specifications with PostgreSQL and local fallback.
* **`/api/v1/requirements/specifications/{id}/graph`**: NetworkX directed traceability graph modeling prompt, requirements, and dependencies.
* **`/api/v1/requirements/specifications/{id}/impact/{req_id}`**: Downstream blast-radius impact analysis for requirement modifications.
* **`/api/v1/requirements/specifications/{id}/coverage`**: Truthful traceability and acceptance criteria coverage reporting.
* **`/api/v1/verification/projects`**: Safe project code archive ingestion, SHA-256 fingerprinting, secret filtering, and AST symbol cataloging.
* **`/api/v1/verification/projects/{id}/link-requirements`**: Deterministic candidate and confirmed requirement-to-code traceability linking.
* **`/api/v1/verification/projects/{id}/runs`**: Containerized test verification runner with strict resource caps and fail-closed host protection.
* **`/api/v1/requirements/specifications/{id}/evidence`**: Requirement-level verification verdicts backed by real test execution outcomes.
* **`/api/v1/regression/analyze`**: AST symbol change impact analysis, modified files classification, and requirement DAG blast-radius propagation.
* **`/api/v1/regression/prioritize`**: Test prioritization using deterministic baseline or predictive ML with transparent fallback.
* **`/api/v1/regression/select`**: Top-k and execution time budget test selection with explicit exclusion reasons.
* **`/api/v1/regression/history`**: Collection and export of genuine test execution observations with strict provenance tracking.
* **`/api/v1/regression/model/status`**: Predictive model status, version, training sample count, and fallback behavior.
* **`/api/v1/repair/analyze/{run_id}`**: Parsing pytest failures, exception tracebacks, and static findings into ranked diagnostic hypotheses.
* **`/api/v1/repair/proposals`**: Candidate patch synthesis with unified diff, risk rating, and deterministic rule templates or local code models.
* **`/api/v1/repair/proposals/{id}/approve`**: Explicit human approval gate transition before live workspace modification.
* **`/api/v1/repair/proposals/{id}/apply`**: Workspace jail-enforced patch application with pre-patch snapshot creation.
* **`/api/v1/repair/proposals/{id}/verify`**: Post-repair verification in isolated Docker containers with before-and-after comparison.
* **`/api/v1/repair/proposals/{id}/rollback`**: Atomic reversion of modified code files to pre-repair snapshot state.
* **`/api/v1/repair/history`**: Immutable audit ledger tracking all repair proposals, approvals, applications, and rollbacks.
* **`/api/v1/repair/runtime/status`**: Subsystem telemetry for deterministic repair engine, Ollama code model, and Docker sandbox.

---

## 8. Current Implementation Status & Roadmap

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **Project Foundation, Architecture & Telemetry** | **Completed** |
| **Phase 2** | **Custom Prompt Intelligence Engine (Classifier, Scoring, Optimizer)** | **Completed** |
| **Phase 3** | **Requirement Extraction & Traceability DAG (NetworkX, Validation, Blast Radius)** | **Completed** |
| **Phase 4** | **Code Evidence & Automated Verification Engine (Ingestion, Traceability, Sandbox)** | **Completed** |
| **Phase 5** | **Predictive Regression Testing Engine (AST Impact, Prioritizer, ML Model)** | **Completed** |
| **Phase 6** | **Failure-Guided Automated Code Repair Engine (AST Jailing, Diffs, Rollback, Lifecycle)** | **Completed** |
| **Phase 7** | **Model Lab, Experiment Tracking & Benchmarks** | Planned |
| **Phase 8** | **System Integration & Final Project Defense** | Planned |

See [docs/AUTOMATED_REPAIR.md](file:///c:/promptforge-ai/docs/AUTOMATED_REPAIR.md), [docs/PREDICTIVE_REGRESSION.md](file:///c:/promptforge-ai/docs/PREDICTIVE_REGRESSION.md), [docs/CODE_VERIFICATION.md](file:///c:/promptforge-ai/docs/CODE_VERIFICATION.md), [docs/REQUIREMENT_TRACEABILITY.md](file:///c:/promptforge-ai/docs/REQUIREMENT_TRACEABILITY.md), and [docs/IMPLEMENTATION_ROADMAP.md](file:///c:/promptforge-ai/docs/IMPLEMENTATION_ROADMAP.md) for detailed documentation.
