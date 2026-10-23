# Failure-Guided Automated Code Repair Engine

PromptForge AI: An Intelligent Prompt-to-Software Engineering Platform with Requirement Traceability, Predictive Regression Testing, and Automated Verification.

---

## 1. Executive Summary & Architectural Philosophy

Automated program repair (APR) in modern software engineering is frequently plagued by two fatal flaws:
1. **Unbounded Generative Hallucination**: Blindly feeding broken files to cloud LLMs, which hallucinate APIs, destroy formatting, introduce security vulnerabilities, or overwrite working code.
2. **Execution Insecurity**: Applying unvetted patches directly to live environments without prior human approval or running untrusted code on the host machine.

The **PromptForge AI Failure-Guided Automated Code Repair Engine (Phase 6)** solves these challenges through an evidence-first, safety-hardened, human-in-the-loop repair architecture:
- **No Fabricated Causes**: Root-cause hypotheses are derived exclusively from genuine verification run artifacts (pytest assertion diffs, Python tracebacks, AST syntax trees, and static analysis findings).
- **Truthful Defect Classification**: Environmental issues (such as Docker daemon offline or container timeouts) are strictly classified as `ENVIRONMENT_ISSUE` and never blamed on source code defects.
- **Multi-Tier Generation**: A deterministic rule engine runs first for proven bug patterns (operator inversion, boundary inequalities, dictionary lookups), falling back to a pluggable local code model (`qwen2.5-coder` via Ollama) when available.
- **Strict Human Approval Gate**: Automated patches are *never* applied without explicit user approval. State transitions strictly enforce `proposed` $\rightarrow$ `approved` $\rightarrow$ `applied` $\rightarrow$ `verified`.
- **Workspace Jail & Integrity Defense**: Traversal attempts (`..`) are denied, file SHA-256 hashes are verified against stale drift, and Python AST syntax is validated before disk writes.
- **Immutable Rollback Snapshots**: Pre-patch copies are snapshotted in `backend/data/repair/snapshots/{repair_id}/` prior to patch application, enabling instantaneous, deterministic rollback.
- **Zero Host Execution Fallback**: Post-repair re-verification runs exclusively inside isolated Docker sandbox containers. If Docker is offline, verification truthfully enters `blocked` status rather than risking host execution.

---

## 2. System Architecture & Repair Pipeline

```
+-----------------------------------------------------------------------------------+
|                           Verification Failure Stream                             |
|               (Pytest Assertion Diffs, Exception Tracebacks, AST Findings)        |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            FailureAnalyzer Service                                |
|  - Classify Category: assertion_failure | exception | syntax_error | env_blocked   |
|  - Classify Defect:   code_defect | test_defect | environment_issue               |
|  - Correlate Artifacts & Traceability Links (Phase 4 / Phase 3 REQ-IDs)           |
|  - Rank Hypotheses with Concrete Evidence Basis & Confidence Scores               |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        RepairCandidateGenerator Service                           |
|  - Tier 1: Deterministic Rule Engine (Arithmetic, Boundary, KeyError, Colons)     |
|  - Tier 2: Pluggable Local Code Model Adapter (Ollama: qwen2.5-coder)             |
|  - Security Filter: Block / Restrict 'auth', 'token', 'crypto', 'password'        |
|  - Compute Unified Diff, SHA-256 Hashes, Risk Level (low, med, high, restricted)  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                      Developer Review & Approval Gate (UI)                        |
|  - State: PROPOSED -> [Reject] -> REJECTED                                        |
|                    -> [Approve] -> APPROVED                                       |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                              SecurePatcher Service                                |
|  - Enforce Workspace Jail (Reject Path Traversal & Escapes)                       |
|  - Verify Original SHA-256 Fingerprint (Reject Stale Baseline Drift)              |
|  - Validate Python AST Syntax on Patched String                                   |
|  - Create Immutable Snapshot: data/repair/snapshots/{repair_id}/target.py.orig    |
|  - Write Patched Content to Workspace (State: APPLIED)                            |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                    Isolated Verification & Comparison Engine                      |
|  - Re-run Verification in Isolated Docker Container                               |
|  - Compare Before vs After Test Outcomes (Pre vs Post Failures)                   |
|  - Post-Run Passed -> VERIFIED                                                    |
|  - Post-Run Failed -> FAILED_VERIFICATION (Safe Rollback Prompted)                |
|  - Docker Unavailable -> BLOCKED (No host execution fallback)                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            Immutable Audit Trail                                  |
|         Records: PROPOSE -> APPROVE -> APPLY -> VERIFY -> (ROLLBACK)             |
+-----------------------------------------------------------------------------------+
```

---

## 3. Failure Analysis Taxonomy

The `FailureAnalyzer` parses real verification logs and assigns strongly-typed categories and classifications:

### Failure Categories
| Category | Definition | Evidence Basis |
| :--- | :--- | :--- |
| `assertion_failure` | Pytest assertion expression failed (e.g. `assert 8 == 2`) | Pytest assertion diff lines (`E assert 8 == 2`) |
| `exception` | Unhandled runtime exception (e.g. `ZeroDivisionError`, `KeyError`) | Traceback exception frames and message |
| `syntax_error` | Code or patch contains invalid Python syntax | AST parser errors or compiler exceptions |
| `import_error` | Missing or cyclical module imports | `ModuleNotFoundError` or `ImportError` tracebacks |
| `static_analysis_violation` | AST inspection or linter violations | Static analyzer finding lines |
| `timeout` | Execution exceeded hard container time limit | Container timer termination signal |
| `environment_blocked` | Docker daemon offline or container runner unavailable | Docker socket or adapter connection failure |

### Defect Classifications
- `code_defect`: The defect originates in source implementation code under test.
- `test_defect`: The test itself asserts an invalid contract or contains invalid mock setups.
- `environment_issue`: The infrastructure (Docker, network, permissions) prevented execution; **never** classified as a code defect.
- `unresolved`: Evidence is ambiguous and requires developer investigation.

---

## 4. Multi-Tier Candidate Generation Strategy

The `RepairCandidateGenerator` produces reviewable `RepairProposal` objects:

### Tier 1: Deterministic Rule Engine
Applies verifiable, zero-hallucination code transformations to established defect patterns:
1. **Operator Inversion**: Corrects inverted arithmetic operators (e.g., `+` $\rightarrow$ `-` in subtraction routines).
2. **Boundary Condition & Inequality**: Adjusts off-by-one errors (e.g., `>` $\rightarrow$ `>=` or `<` $\rightarrow$ `<=`).
3. **Boolean Return Inversion**: Fixes inverted boolean return statements (`return False` $\rightarrow$ `return True`).
4. **Dictionary Lookup Hardening**: Replaces vulnerable direct bracket lookups (`self.cache[key]`) with safe default lookups (`self.cache.get(key, None)`).
5. **Syntax Formatting**: Adds missing colons after control flow or function definition headers (`def`, `class`, `if`, `while`).

### Tier 2: Pluggable Local Code Model Adapter
When enabled and reachable:
- Uses local inference runtime via Ollama (`http://localhost:11434/api/generate`).
- Targets `qwen2.5-coder:7b` or `qwen2.5-coder:1.5b`.
- Operates under strict system prompting instructing the model to return *only* the corrected file content without markdown banter.
- Bound by short timeouts (30 seconds) and local privacy constraints.

### Security Restriction Filter
Any target file path containing security-sensitive keywords:
- `auth`, `password`, `secret`, `token`, `crypto`, `jwt`, `credential`, `payment`, `session`
is automatically assigned `RiskLevel.SECURITY_RESTRICTED`. Automated patches targeting security paths are explicitly flagged in the UI to require elevated manual inspection.

---

## 5. Patch Safety, Integrity & Rollback Service

The `SecurePatcher` enforces strict security invariants before touching workspace files:

1. **Workspace Jail Defense**:
   - Rejects target paths containing traversal patterns (`..`), root slashes (`/`), or backslashes (`\`).
   - Resolves target path against project root and verifies `target_file.relative_to(project_root)`.

2. **Original Hash Integrity Check**:
   - Calculates `sha256(current_file_content)`.
   - Compares against `proposal.original_artifact_hash`.
   - If hashes differ, rejects patch application with a `Stale Patch Rejected` error, protecting against overwriting concurrent developer edits.

3. **Python AST Syntax Pre-Validation**:
   - Runs `ast.parse(proposal.patched_content)`.
   - If a `SyntaxError` is detected, aborts application and preserves the original file untouched.

4. **Snapshot-Backed Rollback**:
   - Copies pre-patch content to `backend/data/repair/snapshots/{repair_id}/{filename}.orig`.
   - Rollback restores the exact pre-patch byte sequence and resets proposal status to `rolled_back`.

---

## 6. Lifecycle State Machine & Coordinator

```
[PROPOSED] 
    |---> [Reject] ---> [REJECTED]
    |---> [Approve] ---> [APPROVED]
                             |
                             v
                         [APPLIED] <-------------------+
                             |                         |
                             +---> [Verify in Docker]  |
                             |                         |
                             v                         |
        +--------------------+--------------------+    |
        |                                         |    |
        v                                         v    |
    [VERIFIED]                       [FAILED_VERIFICATION]
        |                                         |
        +-------------------+---------------------+
                            |
                            v
                       [Rollback]
                            |
                            v
                      [ROLLED_BACK]
```

### Invariants:
1. `apply_proposal()` raises HTTP 400 if proposal is not `APPROVED`.
2. `verify_proposal()` raises HTTP 400 if proposal is not `APPLIED`.
3. `verify_proposal()` transitions to `BLOCKED` if Docker is offline, returning HTTP 503 without corrupting the proposal state.
4. `rollback_proposal()` is permitted from `APPLIED`, `FAILED_VERIFICATION`, or `VERIFIED`.

---

## 7. REST API Endpoints

All endpoints are mounted under `/api/v1/repair`:

| Method | Endpoint | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/analyze/{run_id}` | None | Analyzes test run failures into structured diagnostic reports. |
| `GET` | `/failures/{failure_id}` | None | Retrieves individual failure analysis report. |
| `POST` | `/proposals` | `GenerateProposalRequest` | Generates a targeted repair candidate with unified diff. |
| `GET` | `/proposals` | Query: `project_id` | Lists all repair proposals for a project. |
| `GET` | `/proposals/{repair_id}` | None | Retrieves a specific proposal by repair ID. |
| `POST` | `/proposals/{repair_id}/approve` | `ProposalDecisionRequest` | Explicitly approves a repair candidate. |
| `POST` | `/proposals/{repair_id}/reject` | `ProposalDecisionRequest` | Rejects a proposal with optional reason. |
| `POST` | `/proposals/{repair_id}/apply` | None | Safely applies patch to workspace with snapshot creation. |
| `POST` | `/proposals/{repair_id}/verify` | None | Re-verifies patch inside isolated Docker container. |
| `POST` | `/proposals/{repair_id}/rollback` | None | Restores original file from immutable snapshot. |
| `GET` | `/history` | Query: `repair_id` | Returns immutable audit trail of lifecycle events. |
| `GET` | `/runtime/status` | None | Reports real-time status of rule engine, Ollama model, and Docker. |

---

## 8. Frontend Repair Studio (`RepairPage.tsx`)

The Frontend Repair Studio provides an intuitive, high-contrast engineering console:
1. **Runtime Status Bar**: Real-time pills for Rule Engine (Deterministic), Local Code Model (Ollama), and Docker Sandbox.
2. **Preset Defect Scenarios**:
   - *Arithmetic Operator Defect*: `calc.py` returning `a + b` instead of `a - b`.
   - *Off-By-One Boundary Defect*: `validator.py` checking `age > 18` instead of `age >= 18`.
   - *KeyError Crash*: `cache.py` missing `.get(k, None)` fallback.
3. **Failure Diagnosis Panel**: Lists active failures, suspected file and line numbers, and expandable tracebacks.
4. **Ranked Hypotheses Card**: Displays ranked root causes with confidence percentages and evidence basis.
5. **Unified Diff Viewer**: High-contrast diff displaying removed lines in red, added lines in green, and hunk headers in blue.
6. **State-Gated Lifecycle Action Buttons**:
   - `Approve Proposal`
   - `Reject Proposal`
   - `Apply Patch to Workspace`
   - `Verify in Docker Sandbox`
   - `Rollback to Snapshot`
7. **Before & After Test Verification Audit**: Side-by-side metric cards comparing pre-repair failure count with post-repair failure count, highlighting fixed tests.
8. **Immutable Audit Ledger**: Real-time table displaying timestamped state transitions and actors.

---

## 9. Verification & Test Suite

The Phase 6 Automated Code Repair Engine is backed by extensive automated test suites:

### Backend Tests (`pytest`):
- `tests/test_repair_failure_analyzer.py`: Validates assertion diff parsing, exception traceback extraction, static findings, requirement linking, and Docker offline categorization.
- `tests/test_repair_generator.py`: Tests deterministic operator inversion, boundary inequality repair, unified diff formatting, and security path filtering.
- `tests/test_repair_patcher.py`: Verifies workspace jail path traversal defense, hash drift rejection, AST syntax validation, snapshot creation, and rollback restoration.
- `tests/test_repair_lifecycle.py`: Tests state machine transitions (`PROPOSED` $\rightarrow$ `APPROVED` $\rightarrow$ `APPLIED` $\rightarrow$ `VERIFIED`), approval gating, and blocked sandbox behavior.
- `tests/test_repair_api.py`: Comprehensive end-to-end API test exercising the entire workflow through FastAPI ASGI client.
- **Result**: **68 tests passed, 2 skipped** (offline DB and live Docker integration gracefully skipped).

### Frontend Tests (`vitest`):
- `src/tests/RepairPage.test.tsx`: Validates rendering of header diagnostics, preset defect scenarios, workflow controls, and studio sections.
- **Result**: **16 tests passed across 7 test files**.
- Production build: `npm run build` compiles with 0 errors via TypeScript and Vite.
