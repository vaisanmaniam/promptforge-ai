# Code Evidence & Automated Verification Engine

## 1. Architectural Overview & Data Flow

PromptForge AI **Phase 4** establishes the **Code Evidence & Automated Verification Engine**.
This engine forms the empirical bridge between the high-level software requirements extracted in Phase 3 and tangible source code artifacts, test executions, and static safety evidence.

```
                  ┌───────────────────────────────┐
                  │    Uploaded Source Archive    │ (ZIP / JSON Stream)
                  └───────────────┬───────────────┘
                                  │
                   ┌──────────────▼──────────────┐
                   │  Artifact Ingestion Service │
                   │  - Path Traversal Defense   │
                   │  - Secret / Dependency Strip│
                   │  - SHA-256 Fingerprinting   │
                   │  - AST Symbol Extraction    │
                   └──────────────┬──────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
     ┌───────────▼─────────────┐     ┌─────────────▼─────────────┐
     │ Code Traceability Engine│     │    Verification Engine    │
     │ - Explicit REQ Markers  │     │ - Static AST Inspection   │
     │ - AST Symbol Matching   │     │ - Test Discovery (pytest) │
     │ - Candidate vs. Confirmed│    │ - Verdict Mapping Formula │
     └───────────┬─────────────┘     └─────────────┬─────────────┘
                 │                                 │
                 │                 ┌───────────────▼───────────────┐
                 │                 │    Docker Execution Adapter   │
                 │                 │ - Network: none               │
                 │                 │ - Memory: 512MB / CPU: 1.0    │
                 │                 │ - Read-Only Source Volume     │
                 │                 │ - Fail-Closed when Stopped    │
                 │                 └───────────────┬───────────────┘
                 │                                 │
                 └────────────────┬────────────────┘
                                  │
                  ┌───────────────▼───────────────┐
                  │ Requirement Evidence Report   │
                  │ (Verified / Failed / Unverified│
                  │  with Truthful Real Metrics)  │
                  └───────────────────────────────┘
```

---

## 2. Ingestion Security & Sanitization

Untrusted user uploads are handled under strict defensive constraints:

1. **Volume & Size Limits**:
   - Total archive size capped at 20MB (`MAX_UPLOAD_SIZE_BYTES`).
   - Uncompressed volume capped at 50MB to neutralize decompression bombs (Zip Bombs).
   - Entry count strictly limited to 500 files (`MAX_UPLOAD_FILE_COUNT`).
2. **Path Traversal Rejection**:
   - Every entry path is normalized and inspected. Entries containing `..`, leading slashes (`/`), drive letters (`C:`), or directory escape patterns are rejected immediately with `IngestionSecurityError`.
3. **Symlink Defense**:
   - Archive entries with POSIX symlink bits (`0o120000`) or special file types are discarded.
4. **Secret & Credential Filtering**:
   - Environment files (`.env`, `.env.local`), private keys (`*.pem`, `*.key`, `id_rsa*`), and credential stores (`credentials.json`, `secrets.yaml`) are automatically filtered and omitted from ingestion.
5. **Dependency Directory Discard**:
   - Build artifacts and dependency caches (`node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.git`) are stripped to ensure clean reproducible workspaces.
6. **Integrity Fingerprinting**:
   - Every accepted artifact is fingerprinted with a standard SHA-256 checksum and cataloged with line counts, language type, and AST symbols.

---

## 3. Requirement-to-Code Traceability Semantics

Traceability links represent directed connections from a Phase 3 requirement (`REQ-xxx`) to a code symbol or test case.

### 3.1 Link Types
- **`candidate_implementation`**: Heuristic or static discovery indicating a source function/class likely satisfies the requirement.
- **`confirmed_implementation`**: Developer-reviewed or structurally validated implementation link.
- **`candidate_test`**: Discovered test asserting requirement behavior.
- **`confirmed_test`**: Confirmed test case providing official verification evidence for the requirement.

### 3.2 Linking Heuristics & Confidence Scoring
1. **Explicit Requirement Markers** (`confidence = 0.95`):
   - Presence of `REQ-001` or `req_001` in code comments, docstrings, or test function names (e.g. `def test_req_001_cache_eviction()`).
2. **AST Symbol Keyword Matching** (`confidence = 0.60 – 0.85`):
   - Alphanumeric tokens extracted from the requirement headline matched against Python AST classes and function signatures (`LRUCache.get`, `verify_jwt`).
3. **Module & File Conventions** (`confidence = 0.50`):
   - Matching filenames (`cache.py`, `auth.py`).

Candidate links are never counted as proof that a requirement is satisfied.

---

## 4. Isolated Docker Execution & Fail-Closed Policy

### 4.1 Sandbox Container Constraints
When testing Python projects, tests execute within an isolated container:
- **No Network Access**: Container runs with `--network none`.
- **Resource Caps**: Memory capped at 512MB (`--memory 512m`), CPU capped at 1.0 core (`--cpus 1.0`).
- **Read-Only Source Volume**: Source snapshot mounted `:ro` (`/workspace:ro`).
- **Execution Timeouts**: Subprocess timeout capped at 15 seconds. If exceeded, the container is forcibly terminated (`docker kill`).
- **No Host Mounts**: Ephemeral execution containers have zero access to host filesystems, secrets, or Docker sockets.
- **Argument Array Execution**: Commands are passed as strict argument lists (`['pytest', '-v']`) without shell string interpolation.

### 4.2 Fail-Closed Guarantee
PromptForge AI mandates that **untrusted uploaded code must never execute directly on the host machine**.
- If the Docker CLI is missing, or the Docker Desktop engine daemon is stopped, the runner reports `ExecutionStatus.UNAVAILABLE`.
- It **fails closed**: the system refuses to run tests on the host OS.

---

## 5. Requirement Verification Verdicts & Coverage Formulas

### 5.1 Verification Lifecycle
Verification runs transition through deterministic states:
- `queued`: Enqueued for execution.
- `running`: Container spawned.
- `passed`: Tests completed with container exit code 0.
- `failed`: Tests completed with non-zero exit code.
- `timed_out`: Exceeded execution time limit.
- `unavailable`: Docker daemon offline; execution prohibited.
- `error`: Infrastructure failure.

### 5.2 Requirement-Level Verdict Rules
A passing test suite does not imply all requirements are verified. Each requirement $R$ receives an individual verdict:
1. **`FAILED`**: If any linked test case for $R$ failed during execution.
2. **`VERIFIED`**: If at least one linked test for $R$ executed and passed, 0 linked tests failed, AND static code analysis passed without syntax errors.
3. **`UNVERIFIED`**: If no test cases are linked to $R$, or if linked tests were not executed in the run, or if the run was `unavailable`.

### 5.3 Truthful Coverage Metrics
- **Confirmed Code Coverage**: $\frac{\text{Requirements with Confirmed Code}}{\text{Total Requirements}}$
- **Test Linking Coverage**: $\frac{\text{Requirements with Linked Tests}}{\text{Total Requirements}}$
- **Verification Coverage**: $\frac{\text{Requirements with VERIFIED Verdict}}{\text{Total Requirements}}$

Unknown, skipped, or unverified requirements are strictly excluded from the verification numerator.

---

## 6. REST API Reference

| Method | Path | Summary |
|---|---|---|
| `POST` | `/api/v1/verification/projects` | Ingest project archive (ZIP multipart upload) |
| `POST` | `/api/v1/verification/projects/json` | Ingest project code via JSON dictionary |
| `GET` | `/api/v1/verification/projects` | List all ingested projects |
| `GET` | `/api/v1/verification/projects/{project_id}` | Retrieve project report and manifest data |
| `GET` | `/api/v1/verification/projects/{project_id}/artifacts` | List inventoried artifacts and AST symbols |
| `POST` | `/api/v1/verification/projects/{project_id}/link-requirements` | Generate candidate traceability links with a specification |
| `GET` | `/api/v1/verification/projects/{project_id}/traceability` | Retrieve candidate and confirmed traceability links |
| `POST` | `/api/v1/verification/projects/{project_id}/confirm-link/{link_id}` | Confirm or reject a candidate link |
| `POST` | `/api/v1/verification/projects/{project_id}/runs` | Trigger isolated test verification run |
| `GET` | `/api/v1/verification/runs/{run_id}` | Retrieve execution outputs, logs, and verdicts |
| `GET` | `/api/v1/requirements/specifications/{spec_id}/evidence` | Get requirement evidence verdicts and updated coverage |
| `GET` | `/api/v1/verification/docker-status` | Probe live Docker daemon readiness and fail-closed policy |

---

## 7. Known Limitations & Roadmap

- **Supported Languages**: Phase 4 focuses on Python 3.11 with `pytest`. TypeScript/Node.js and Java/JUnit sandbox runners are architected for subsequent expansion.
- **Docker Dependency**: Containerized execution requires a running Docker engine. Host fallback is intentionally barred for security.
- **Next Phase (Phase 5)**: Predictive Regression Intelligence using LightGBM will leverage the traceability links and execution histories created here to prioritize high-risk test execution.
