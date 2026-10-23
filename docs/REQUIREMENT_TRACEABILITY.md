# Requirement Intelligence & Traceability Engine

## 1. Overview & Architectural Motivation

In traditional software development and AI-assisted coding, the gap between natural language developer prompts and downstream implementation artifacts frequently leads to **silent drift**, **unvalidated assumptions**, and **untestable code**.

**PromptForge AI Phase 3** establishes the **Requirement Intelligence & Traceability Engine**, creating a verifiable bridge from raw user prompts to formal software requirements, acceptance criteria, and directed traceability graphs (`networkx`).

```
                    ┌────────────────────────┐
                    │      Source Prompt     │
                    └───────────┬────────────┘
                                │
                 ┌──────────────▼─────────────┐
                 │    Component & Ambiguity   │ (Phase 2 Intelligence)
                 │     Analysis & Profiler    │
                 └──────────────┬─────────────┘
                                │
                 ┌──────────────▼─────────────┐
                 │   Requirement Extractor    │
                 │   - Functional             │
                 │   - Technical Constraints  │
                 │   - Non-Functional (NFR)   │
                 │   - Security               │
                 └──────────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
    ┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
    │  Requirement   │  │   NetworkX     │  │   Traceability  │
    │   Validator    │  │  Traceability  │  │   & Coverage   │
    │  (Heuristics & │  │  Directed DAG  │  │    Analyzer    │
    │ Contradictions)│  │ (Blast Radius) │  │(Truthful Metric│
    └────────────────┘  └────────────────┘  └────────────────┘
```

---

## 2. Core Data Schemas

### 2.1 Structured Requirement Model (`RequirementItem`)

Each requirement possesses a deterministic stable identifier (`REQ-001`, `REQ-002`, ...) and strictly typed properties:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Deterministic identifier (`REQ-001`) |
| `title` | `str` | Concise requirement headline |
| `description` | `str` | Full behavioral and functional specification |
| `category` | `RequirementCategory` | `functional`, `technical_constraint`, `nonfunctional`, `security` |
| `priority` | `RequirementPriority` | `critical`, `high`, `medium`, `low` |
| `status` | `RequirementStatus` | `explicit` (user-stated) or `inferred` (engine baseline) |
| `source_text` | `Optional[str]` | Verbatim sentence or matched component that justified extraction |
| `assumptions` | `List[AssumptionItem]` | Linked architectural assumptions requiring confirmation |
| `acceptance_criteria` | `List[AcceptanceCriterion]` | Testable conditions for verification |
| `verification_state` | `VerificationState` | `unverified`, `verified`, `failed` |
| `depends_on` | `List[str]` | Prerequisite requirement IDs |
| `refines` | `List[str]` | Specialized sub-requirement links |

### 2.2 Acceptance Criteria (`AcceptanceCriterion`)

Requirements must define testable acceptance criteria to enable Phase 4 automated verification:

- `id`: Unique identifier (`AC-001`)
- `description`: Verifiable condition or expected behavior
- `verification_type`: `unit_test`, `integration_test`, `static_analysis`, `manual_review`
- `status`: `pending`, `passed`, `failed`

### 2.3 Explicit vs. Inferred Status & Assumptions (`AssumptionItem`)

PromptForge AI does not hallucinate architectural choices silently. When a requirement is inferred (such as standard token authentication or default database dialects), it is:
1. Tagged with `status: "inferred"`.
2. Explicitly linked to an `AssumptionItem` (`ASM-001`) with resolution status `unresolved`.
3. Highlighted in the developer console for confirmation or rejection.

---

## 3. Requirement Extraction Engine

The `RequirementExtractor` deterministically segments prompts using multi-label component detection:

1. **Functional Requirements (`functional`)**:
   - Primary objective requirement capturing the core capability contract.
   - Secondary functional items extracted from clauses, I/O schemas, caching policies, filtering, and concurrency patterns.
2. **Technical Constraints (`technical_constraint`)**:
   - Target runtime (Python 3.11, Node.js, etc.) and web frameworks (FastAPI, Express).
   - Database dialect (PostgreSQL 16, SQLite).
   - Asymptotic computational complexity bounds ($O(1)$, $O(\log N)$).
3. **Non-Functional Requirements (`nonfunctional`)**:
   - Operational latency and throughput thresholds.
   - Concurrency bounds, memory limits, and graceful error degradation.
4. **Security Requirements (`security`)**:
   - Identity verification and password hashing (JWT, bcrypt).
   - Input sanitization, CORS defense, and OWASP Top 10 injection mitigation.

---

## 4. Requirement Validation Rules

The `RequirementValidator` subjects specifications to automated quality checks:

| Rule ID | Severity | Condition | Remediation Guidance |
|---|---|---|---|
| `VAGUE_QUALIFIER` | `warning` | Presence of subjective qualifiers ("fast", "scalable", "user-friendly", "robust") without quantifiable thresholds. | Specify numerical budgets (e.g. latency in ms, QPS, or complexity). |
| `MISSING_ACCEPTANCE_CRITERIA` | `error` | Requirement item with 0 testable acceptance criteria. | Define at least one automated unit test or static assertion. |
| `UNRESOLVED_ASSUMPTION` | `warning` / `info` | Active technical assumptions not yet confirmed by the developer. | Confirm, adjust, or reject the assumption. |
| `SELF_DEPENDENCY` | `error` | Requirement references itself in `depends_on`. | Remove circular self-reference. |
| `CONSTRAINTS_CONFLICT` | `error` | "Standard library only" constraint alongside declared third-party dependencies. | Reconcile dependencies. |
| `ARCHITECTURAL_CONTRADICTION` | `warning` | Stateless architecture alongside in-memory session persistence. | Clarify token or distributed caching strategy. |

---

## 5. NetworkX Directed Traceability Graph

Traceability is modeled as a directed graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ powered by `networkx.DiGraph`:

### 5.1 Node Hierarchy
- **Prompt Root**: `PROMPT-ROOT` (source of intent)
- **Requirements**: `REQ-001`, `REQ-002`, ...
- **Future Hooks**: `CODE-xxx` (Phase 4 code artifacts), `TEST-xxx` (Phase 4 test suites)

### 5.2 Directed Edge Semantics
- `PROMPT-ROOT -> REQ-xxx`: relation `"generates"`
- `REQ-A -> REQ-B`: relation `"depends_on"` (A depends on B)
- `REQ-A -> REQ-B`: relation `"refines"` (A refines B)

### 5.3 Blast-Radius Impact Analysis
When requirement $R$ is modified:
- **Upstream Dependencies**: Ancestors in the dependency DAG that $R$ relies on.
- **Downstream Dependents**: Requirements that directly or transitively rely on $R$.
- **Impact Depth**: Maximum path length across the downstream dependency tree.
- **Risk Level**: Computed based on downstream blast radius and priority (`low`, `medium`, `high`, `critical`).

---

## 6. Truthful Coverage & Zero-Fabrication Guarantee

PromptForge AI enforces strict metric integrity:
- **Prompt-to-Requirement Coverage**: Percentage of requirements tied to prompt roots (100%).
- **Acceptance Criteria Coverage**: Percentage of requirements with verifiable criteria.
- **Assumption Resolution Rate**: Percentage of assumptions confirmed vs unresolved.
- **Code & Test Traceability**: Truthfully reported as `pending_phase_4` rather than fabricating synthetic 100% test passes before execution sandboxes exist.

---

## 7. Storage & Fallback Architecture

Persistence utilizes a hybrid repository (`RequirementRepository`):
- **Primary Store**: Relational tables `requirement_specifications` and `requirement_items` via SQLAlchemy `AsyncSession` when PostgreSQL is online.
- **Local Fallback**: Structured JSON files in `backend/data/specifications/{spec_id}.json` with in-memory caching when PostgreSQL is offline or Docker is unavailable.
- Guarantees 100% test reliability and zero downtime during local development.

---

## 8. REST API Endpoints

All endpoints are mounted under `/api/v1/requirements`:

| Method | Path | Summary |
|---|---|---|
| `POST` | `/api/v1/requirements/extract` | Extract and validate requirements from a prompt |
| `POST` | `/api/v1/requirements/specifications` | Create, validate, and persist a requirement specification |
| `GET` | `/api/v1/requirements/specifications` | List all saved specifications |
| `GET` | `/api/v1/requirements/specifications/{spec_id}` | Retrieve full specification by ID |
| `GET` | `/api/v1/requirements/specifications/{spec_id}/graph` | Retrieve NetworkX directed graph nodes, edges, and cycles |
| `GET` | `/api/v1/requirements/specifications/{spec_id}/impact/{req_id}` | Downstream blast-radius impact analysis for a requirement |
| `GET` | `/api/v1/requirements/specifications/{spec_id}/coverage` | Truthful traceability and acceptance criteria coverage |
| `GET` | `/api/v1/requirements/specifications/{spec_id}/validation` | Quality validation findings and contradiction warnings |
