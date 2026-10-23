# PromptForge AI: Implementation Roadmap

This document outlines the sequential phases, deliverables, dependencies, and explicit acceptance criteria for PromptForge AI.

---

## Phase 1: Project Foundation, Architecture, and AI Development Plan (Current)

**Objective**: Establish a production-grade monorepo, FastAPI backend, React+TypeScript frontend developer console, Docker Compose PostgreSQL service, automated test suites, and core architectural specifications.

### Deliverables
1. Root monorepo structure with `.gitignore`, `.env.example`, and `docker-compose.yml`.
2. PostgreSQL 16 service in Docker Compose with persistent storage and health check.
3. FastAPI backend in Python 3.11 with:
   - Application entry point (`app/main.py`)
   - Configuration via `pydantic-settings` (`app/core/config.py`)
   - Structured logging (`app/core/logging.py`)
   - Liveness probe endpoint (`GET /api/v1/health`)
   - Diagnostic and readiness endpoint (`GET /api/v1/system/status`)
4. Truthful system diagnostics inspecting PostgreSQL, Ollama, model checkpoints, and Docker sandbox.
5. React 18 + TypeScript + Vite + Tailwind CSS frontend shell with developer tool styling.
6. Frontend dashboard displaying real subsystem diagnostics and roadmap placeholders.
7. Backend tests with pytest (6 unit tests passing, live DB integration test properly skipped when offline).
8. Comprehensive documentation: `README.md`, `ARCHITECTURE.md`, `AI_DEVELOPMENT_PLAN.md`, `IMPLEMENTATION_ROADMAP.md`.

### Acceptance Criteria
- [x] Backend imports and boots under Uvicorn.
- [x] `/api/v1/health` returns status `healthy` independently of external services.
- [x] `/api/v1/system/status` inspects real resources and returns valid status enums (`ready`, `unavailable`, `not_configured`, `not_trained`).
- [x] Backend unit tests pass with zero errors or secret leakages.
- [x] Frontend passes unit tests and compiles with `npm run build`.

---

## Phase 2: Custom Prompt Intelligence Engine (Completed)

**Objective**: Analyze incoming software engineering prompts to classify developer intent, detect missing constraints or ambiguities, score quality transparently, and optimize prompt structure.

### Deliverables
1. Schema-validated dataset infrastructure (`ai/datasets/schema.py`, `ai/datasets/validator.py`).
2. Curated seed dataset with 120 verified software engineering examples across 8 task categories with train/val/test splits (`ai/datasets/seed_prompts.json`).
3. Pluggable task classifier interface (`BasePromptClassifier`, `RuleBasedClassifier`, `SklearnPromptClassifier`).
4. Offline reproducible training pipeline (`ai/training/train_classifier.py`) and evaluation pipeline (`ai/evaluation/evaluate_classifier.py`).
5. Multi-label component detector identifying 10 software dimensions with uncertainty handling (`ComponentDetector`).
6. Ambiguity detector flagging subjective terms and generating clarification questions (`AmbiguityDetector`).
7. Deterministic 6-dimension quality scoring engine on a 0–100 scale (`QualityScorer`).
8. Objective-preserving prompt optimizer with assumption exposure and section injection (`PromptOptimizer`).
9. Token-efficiency analyzer supporting exact BPE (`cl100k_base`) and heuristic estimates (`TokenCounter`).
10. FastAPI endpoints: `POST /api/v1/prompts/analyze` and `POST /api/v1/prompts/optimize`.
11. Interactive React developer studio (`PromptIntelligencePage.tsx`).
12. Comprehensive documentation: `docs/PROMPT_INTELLIGENCE.md` and `docs/DATASET_AND_EVALUATION.md`.

### Acceptance Criteria
- [x] Multi-label intent classification achieves 83.3% test accuracy and 0.8405 macro-F1 (vs 12.5% majority baseline).
- [x] Missing-information detector flags underspecified components with explainable evidence.
- [x] Quality scoring calculates transparent 6-dimension breakdown on a 0–100 scale.
- [x] Prompt optimizer preserves user objective and exposes unconfirmed assumptions.
- [x] Token counts explicitly labeled as exact or estimated.
- [x] API endpoints `/api/v1/prompts/analyze` and `/api/v1/prompts/optimize` validate via Pydantic schemas.
- [x] All 23 backend tests and 8 frontend tests pass with zero errors.
- [x] Frontend builds cleanly with zero TypeScript errors.

---

## Phase 3: Requirement Extraction & Traceability Engine

**Status**: **Completed**

**Objective**: Transform natural language requests into schema-validated software requirements and maintain bidirectional traceability to code and tests via NetworkX directed graphs.

### Deliverables
1. Structured Requirement schemas (`RequirementItem`, `AcceptanceCriterion`, `AssumptionItem`, `RequirementSpecification`) and SQLAlchemy models (`models/requirement.py`).
2. Deterministic and explainable requirement extraction engine (`RequirementExtractor`) categorizing items into Functional, Technical Constraints, Non-Functional, and Security.
3. Explicit delineation between user-stated requirements (`status: "explicit"`) and engine-inferred requirements (`status: "inferred"`) linked to formal `AssumptionItem` entities.
4. Rigorous requirement validator (`RequirementValidator`) flagging vague qualifiers without metrics, missing acceptance criteria, unresolved assumptions, and architectural contradictions.
5. NetworkX-backed directed traceability graph (`TraceabilityGraphEngine`) with cycle detection and downstream blast-radius impact analysis.
6. Truthful coverage analysis engine (`CoverageAnalyzer`) reporting real prompt and acceptance criteria metrics while accurately disclosing code/test linking as pending Phase 4.
7. Resilient hybrid repository (`RequirementRepository`) with automatic local fallback when PostgreSQL is offline.
8. REST API endpoints (`/api/v1/requirements/extract`, `/api/v1/requirements/specifications`, `/graph`, `/impact/{req_id}`, `/coverage`, `/validation`).
9. Interactive React developer console (`RequirementsPage.tsx`) with requirement cards, filter pills, interactive SVG directed graph, blast-radius drawer, and validation findings panel.
10. Complete documentation: `docs/REQUIREMENT_TRACEABILITY.md`.

### Acceptance Criteria
- [x] 100% of extracted requirements validate against Pydantic schemas with stable IDs (`REQ-001`, `AC-001`).
- [x] NetworkX directed graph accurately maps prompt roots, requirements, and dependencies with cycle detection.
- [x] Downstream blast-radius impact analysis calculates traversal depth and risk level for requirement modifications.
- [x] Inferred requirements are explicitly labeled with underlying unconfirmed assumptions.
- [x] Truthful coverage reporting guarantees zero fake code/test metrics prior to Phase 4 sandbox execution.
- [x] All 34 backend pytest tests and 10 frontend vitest tests pass cleanly.
- [x] Frontend production bundle compiles with zero TypeScript errors.

---

## Phase 4: Isolated Execution Sandbox & Automated Verification

**Status**: Completed

**Objective**: Safely execute generated code and test suites in containerized isolation without risking host security.

### Deliverables
1. Safe code artifact ingestion (ZIP archive or JSON stream) with zip-bomb caps (20MB, 500 files), path traversal defense, secret stripping (`.env`, `*.key`), and SHA-256 fingerprinting.
2. AST symbol cataloging and candidate/confirmed requirement-to-code and requirement-to-test traceability mapping.
3. Docker execution adapter with non-root user, memory limit (512MB), CPU quota (1.0), network egress disabled (`--network none`), and fail-closed isolation (host fallback forbidden).
4. Automated verification engine running static AST code inspection, test discovery, and containerized pytest suites.
5. Truthful requirement evidence report mapping passing/failing tests to requirements (`VERIFIED`, `FAILED`, `UNVERIFIED`).
6. REST API under `/api/v1/verification/` and `/api/v1/requirements/specifications/{id}/evidence`.
7. React developer console (`VerificationPage.tsx`) with archive upload, preset projects, artifact tables, candidate/confirmed link management, Docker telemetry pill, and execution logs.
8. Comprehensive test suite (42 backend pytest, 12 frontend vitest) and technical guide `docs/CODE_VERIFICATION.md`.

### Acceptance Criteria
- [x] Untrusted code cannot access host filesystem, network, or environment secrets (`--network none`, read-only mounts).
- [x] Fail-closed architecture halts execution when Docker daemon is stopped, never executing on host machine.
- [x] Model assertions are never treated as verification; only container exit code 0 and actual test passes denote success.
- [x] Traceability engine accurately extracts AST symbols and differentiates candidate from confirmed links.
- [x] Evidence report marks requirements `VERIFIED` only when linked tests pass and static checks pass.
- [x] All 42 backend pytest tests and 12 frontend vitest tests pass cleanly.
- [x] Frontend production bundle compiles with zero TypeScript errors.

---

## Phase 5: Predictive Regression Intelligence

**Status**: Completed

**Objective**: Score test failure probabilities from code diffs, AST changes, requirement blast radius, and test history to optimize test execution order.

### Deliverables
1. Change impact service (`change_impact.py`) analyzing modified files, AST functions/classes, Phase 4 requirement links, and Phase 3 DAG blast radius.
2. Explainable deterministic prioritization baseline (`baseline.py`) with transparent multi-signal weights and human-readable decision reasons.
3. Machine learning pipeline (`ai/regression_model/`) with 10-dimensional normalized feature schema, scikit-learn model wrapper, change-level leakage prevention, and Top-k fault recall evaluation.
4. Test selection engine (`selector.py`) implementing `all_tests`, `impact_based`, and `predictive` strategies with top-k and execution budget (ms) limits plus explicit exclusion rationale.
5. Historical test result collector (`history.py`) ingesting genuine verification runs and computing test reliability metrics.
6. Full REST API suite under `/api/v1/regression/...`.
7. Interactive React developer console (`RegressionPage.tsx`) with change presets, blast-radius summary, ranked test table, excluded tests drawer, and Docker sandbox execution trigger.
8. Comprehensive test coverage (56 backend tests, 14 frontend vitest tests) and technical specification `docs/PREDICTIVE_REGRESSION.md`.

### Acceptance Criteria
- [x] Change-impact analysis uses real available code and requirement relationships without inventing Git history.
- [x] Deterministic prioritization works without requiring a trained ML model.
- [x] Predictive training and evaluation pipelines validate schema and reject single-class/insufficient datasets.
- [x] Untrained model is strictly reported as `not_trained` with transparent deterministic fallback.
- [x] Synthetic data is labeled strictly as `synthetic_pipeline_test` and never presented as genuine accuracy metrics.
- [x] Predictive model is evaluated against the deterministic baseline on held-out test splits.
- [x] Test selection and test execution remain separate operations.
- [x] All execution continues through the Phase 4 isolated Docker runner.
- [x] All 56 backend tests (54 passed, 2 integration tests skipped) and 14 frontend tests pass.
- [x] Frontend production bundle compiles cleanly with zero TypeScript errors.

---

## Phase 6: Failure-Guided Automated Code Repair Engine (Completed)

**Objective**: Automatically diagnose verification failures, synthesize verifiable code repairs with deterministic and local model generators, enforce explicit human approval gates, ensure workspace jail safety, and execute isolated re-verification with safe rollback snapshots.

### Deliverables
1. **Failure Analysis Service** (`FailureAnalyzer`):
   - Categorizes failures into `assertion_failure`, `exception`, `syntax_error`, `import_error`, `static_analysis_violation`, `timeout`, and `environment_blocked`.
   - Strictly separates environment obstacles (`ENVIRONMENT_ISSUE`) from source code defects (`CODE_DEFECT`).
   - Links failing tests to Phase 4 AST symbols and Phase 3 requirements.
   - Computes ranked, evidence-backed hypotheses with confidence scores.
2. **Multi-Tier Repair Candidate Generator** (`RepairCandidateGenerator`):
   - Tier 1: Deterministic rule engine for operator inversion, off-by-one boundary inequalities, inverted booleans, and dictionary lookups.
   - Tier 2: Pluggable local code model adapter (`qwen2.5-coder` via Ollama) with temperature limits and short timeouts.
   - Strict security keyword filter flagging `auth`, `password`, `token`, `secret`, `crypto` as `SECURITY_RESTRICTED`.
3. **Patch Safety, Integrity & Rollback Service** (`SecurePatcher`):
   - Enforces workspace jail defense against path traversal (`..`) and absolute path escapes.
   - Validates original SHA-256 fingerprint against stale baseline drift before applying edits.
   - Pre-validates Python AST syntax on patched strings prior to disk write.
   - Creates immutable pre-patch snapshot under `data/repair/snapshots/{repair_id}/` for atomic rollback.
4. **Approval & Verification Lifecycle Coordinator** (`RepairLifecycleCoordinator`):
   - Strict state machine: `proposed` $\rightarrow$ `approved` $\rightarrow$ `applied` $\rightarrow$ `verified` / `failed_verification` / `rolled_back`.
   - Prohibits unauthorized autonomous code modification.
   - Executes post-repair verification exclusively in isolated Docker container.
   - Truthfully marks repair `blocked` if Docker is offline without risking host execution.
5. **REST API Endpoints** (`/api/v1/repair`):
   - Failure diagnosis, proposal synthesis, approve/reject, patch application, Docker verification, snapshot rollback, and audit trail.
6. **Frontend Repair Studio** (`RepairPage.tsx`):
   - Preset defect scenarios, diagnosis view, traceback accordion, high-contrast unified diff viewer, state-gated action buttons, before/after test comparison, and audit trail ledger.

### Acceptance Criteria
- [x] Failures diagnosed strictly from real pytest assertion diffs and tracebacks without hallucinated causes.
- [x] Environmental and Docker daemon obstacles classified strictly as `environment_issue`, never as code defects.
- [x] Security-sensitive paths guarded with `SECURITY_RESTRICTED` risk levels.
- [x] Patches cannot be applied without explicit user approval.
- [x] Workspace jail defenses and hash drift checks prevent arbitrary file overwrite.
- [x] Immutable snapshots enable instant, deterministic rollback.
- [x] Post-repair re-verification runs in containerized isolation; untrusted code never executed on host.
- [x] All 70 backend tests (68 passed, 2 integration tests skipped) and 16 frontend tests pass.
- [x] Production build compiles cleanly with zero TypeScript errors.

---

## Phase 7: Model Training, Evaluation, and MLflow Experiment Tracking

**Objective**: Provide reproducible training pipelines, dataset versioning, and rigorous evaluation.

### Deliverables
1. DVC / MLflow integration for model registry and dataset versioning.
2. Fine-tuning scripts for prompt classification and requirement extraction.
3. Standardized evaluation suite (pass@1, pass@k, requirement recall, APFD).
4. Model Lab frontend page displaying live MLflow experiment comparisons.

### Acceptance Criteria
- Reproducible model training commands documented and tested.
- Zero fabricated metrics; all numbers derived from actual test executions.

---

## Phase 8: Final System Integration & Project Defense Preparation

**Objective**: Complete end-to-end integration, performance benchmarking, defense documentation, and demonstration walkthrough.

### Deliverables
1. End-to-end user workflows from prompt to verified code repository.
2. Comprehensive project report and architectural diagrams.
3. Demonstration test suite with recorded benchmark results.
4. Production Docker Compose deployment configuration.
