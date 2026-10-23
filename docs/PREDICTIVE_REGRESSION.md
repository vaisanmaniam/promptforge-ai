# PromptForge AI — Predictive Regression Testing Engine Specification

## 1. Executive Summary

Phase 5 introduces the **Predictive Regression Testing Engine** into PromptForge AI.
The engine addresses a fundamental testing bottleneck in rapid software development: executing full test suites on every incremental change is computationally expensive, yet naive heuristic test selection risks missing critical regressions.

PromptForge AI combines:
1. **Structural AST Change Impact Analysis**: Identifies added/modified/deleted files, extracted Python function and class symbols, and dependency topologies.
2. **Phase 3 Requirement Blast-Radius Propagation**: Propagates modified code artifacts to functional and security requirements via Phase 4 traceability links, computing downstream impact depth across the NetworkX directed acyclic graph (DAG).
3. **Explainable Deterministic Prioritization Baseline**: Provides an explainable, multi-factor scoring algorithm that guarantees actionable rankings and transparent rationales even when no machine learning model is trained.
4. **Predictive Machine Learning Engine**: Employs scikit-learn models (`RandomForestClassifier`, `LogisticRegression`) to predict regression detection probabilities ($P(\text{failure})$), strictly enforcing dataset schema validation, change-level grouping to prevent data leakage, and honest evaluation against the deterministic baseline.
5. **Truthful Telemetry & Fallback**: Starts in an explicit `not_trained` status, falling back to the deterministic baseline with transparent UI disclosure until trained on genuine observations.

---

## 2. Architecture & Data Flow

```
                      +---------------------------------------+
                      | Code Modification (Changed Files/Diff)|
                      +-------------------+-------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |         ChangeImpactService           |
                      | - AST Symbol Extraction               |
                      | - Phase 4 Traceability Links          |
                      | - Phase 3 DAG Blast-Radius Analysis   |
                      +-------------------+-------------------+
                                          |
                      +-------------------+-------------------+
                      |                                       |
                      v                                       v
         +-------------------------+             +-------------------------+
         | Deterministic Baseline  |             | Feature Extractor (10d) |
         | Multi-Factor Heuristic  |             +------------+------------+
         +------------+------------+                          |
                      |                                       v
                      |                         +---------------------------+
                      |                         | Predictive ML Model       |
                      |                         | - Default: 'not_trained'  |
                      |                         | - Trained: scikit-learn   |
                      |                         +-------------+-------------+
                      |                                       |
                      |      +--------------------------------+
                      |      | (Fallback when untrained)
                      v      v
         +----------------------------------------------------+
         |                 TestSelector                       |
         | Strategies: 'all_tests', 'impact_based', 'predict' |
         | Filters: Top-K Cutoff, Execution Time Budget (ms)  |
         | Outputs: Ranked Selected Tests + Excluded Reasons  |
         +-------------------------+--------------------------+
                                   |
                                   v
         +----------------------------------------------------+
         |       Isolated Docker Runner (Phase 4 Sandbox)     |
         |         --network none, 512MB RAM, 1 CPU quota     |
         +-------------------------+--------------------------+
                                   |
                                   v
         +----------------------------------------------------+
         |           TestHistoryRepository                    |
         | Records genuine observations (Label 1/0)           |
         +----------------------------------------------------+
```

---

## 3. Change Impact Analysis

Implemented in `app.services.regression.change_impact.ChangeImpactService`.

### 3.1 Analysis Pipeline
1. **File Categorization**: Classifies provided files into `added`, `modified`, or `deleted` relative to cataloged project artifacts.
2. **AST Symbol Extraction**: Uses Python's native `ast` module to extract classes, functions, and methods modified in the change.
3. **Requirement Mapping**: Resolves Phase 4 `implements` links to identify directly affected requirement IDs (`REQ-xxx`).
4. **Graph Blast-Radius Propagation**: Queries Phase 3 `TraceabilityGraphEngine.analyze_impact()` to traverse downstream descendants in the requirement dependency DAG, computing traversal depth and dependent requirement IDs.
5. **Candidate Test Discovery**: Identifies tests that:
   - Were directly modified (`is_test = True`).
   - Verify affected requirements via Phase 4 `verifies` links.
   - Match or invoke changed AST function/class symbols.

---

## 4. Deterministic Prioritization Baseline

Implemented in `app.services.regression.baseline.DeterministicPrioritizer`.

### 4.1 Scoring Formula

The deterministic regression risk score $S_{\text{det}} \in [0.05, 1.0]$ is computed as:

$$S_{\text{det}} = W_{\text{direct}} F_{\text{direct}} + W_{\text{req}} F_{\text{req}} + W_{\text{prio}} F_{\text{prio}} + W_{\text{blast}} F_{\text{blast}} + W_{\text{hist}} F_{\text{hist}}$$

Where weights sum to $1.0$:
- $W_{\text{direct}} = 0.35$: Direct test modification ($1.0$), test method name match ($0.8$), or symbol reference ($0.6$).
- $W_{\text{req}} = 0.25$: Direct requirement link ($1.0$) or downstream blast-dependent link ($0.7$).
- $W_{\text{prio}} = 0.15$: Requirement priority weight ($\text{Critical} = 1.0$, $\text{High} = 0.75$, $\text{Medium} = 0.50$, $\text{Low} = 0.25$).
- $W_{\text{blast}} = 0.15$: Blast-radius depth factor: $\min(1.0, \text{depth} / 3.0)$.
- $W_{\text{hist}} = 0.10$: Historical failure rate $\in [0.0, 1.0]$ if genuine history exists; $0.0$ if no prior records exist.

### 4.2 Missing Data Behavior
If no historical test execution records exist, $F_{\text{hist}} = 0.0$ and the engine generates an explicit explanation:
`"No prior execution history recorded; historical success was not assumed."`
Missing historical data is **never** silently treated as a passed test.

---

## 5. Machine Learning Pipeline

Located in `ai/regression_model/`.

### 5.1 Normalized Feature Schema (10 Dimensions)
| Feature Name | Type | Range | Description |
|---|---|---|---|
| `change_file_count` | `int` | $[1, \infty)$ | Number of files modified in the change |
| `is_direct_test_change` | `int` | $\{0, 1\}$ | 1 if test file itself was directly modified |
| `symbol_overlap_count` | `int` | $[0, \infty)$ | Count of overlapping/invoked AST symbols |
| `requirement_priority_weight` | `float` | $[0.0, 1.0]$ | Normalized priority of linked requirement |
| `dependency_distance` | `int` | $[0, \infty)$ | DAG graph distance from change to test requirement |
| `blast_radius_depth` | `int` | $[0, \infty)$ | Downstream impact depth from Phase 3 graph |
| `is_confirmed_link` | `int` | $\{0, 1\}$ | 1 if traceability link is confirmed by developer |
| `historical_failure_rate` | `float` | $[0.0, 1.0]$ | Observed failure frequency in past runs |
| `has_historical_data` | `int` | $\{0, 1\}$ | Binary indicator for missing history |
| `historical_duration_normalized` | `float` | $[0.0, 1.0]$ | Average execution duration scaled by 5000ms |

### 5.2 Training Integrity & Leakage Prevention
- **Change-Level Grouping**: All observations belonging to the same `change_id` are placed strictly into either the training or held-out validation split. Observations from the same change never cross split boundaries.
- **Minimum Thresholds**: Requires $\ge 10$ samples with both positive ($1$) and negative ($0$) classes. Single-class datasets refuse training with status `single_class_detected`.
- **Synthetic Data Isolation**: Synthetic samples have `is_synthetic = True` and `label_provenance = "synthetic_pipeline_test"`. They are used exclusively to test the training and evaluation pipelines.

---

## 6. Test Selection Strategies & Budgeting

Implemented in `app.services.regression.selector.TestSelector`.

1. **`all_tests`**: Evaluates all discovered tests, preserving risk rankings for execution order.
2. **`impact_based`**: Selects tests structurally linked to changed files, changed symbols, or affected requirements. Tests with zero structural impact are moved to `excluded_tests`.
3. **`predictive`**: Ranks tests by ML failure probability $P(\text{failure})$. If the model is `not_trained`, automatically falls back to deterministic ranking with explicit disclosure.

### Bounds & Exclusions
- **Top-$K$ Limit**: Keeps only the top $K$ ranked tests. Excluded tests report: `Exceeded Top-K selection limit (ranked #4 with score 0.32)`.
- **Execution Budget (ms)**: Accumulates estimated test durations and halts selection once budget is exceeded, reporting: `Exceeded execution time budget of 500ms (cumulative 550ms)`.

---

## 7. REST API Reference

All endpoints are mounted under `/api/v1/regression`:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Run structural change impact analysis |
| `POST` | `/prioritize` | Rank tests with chosen strategy |
| `POST` | `/select` | Filter tests by strategy, top-k, and time budget |
| `GET` | `/analyses/{id}` | Retrieve stored change impact analysis |
| `GET` | `/history` | Retrieve historical test observations |
| `POST` | `/history/record` | Ingest verification run outcomes into history |
| `GET` | `/model/status` | Telemetry on model state, version, and fallback |
| `POST` | `/model/train` | Validate dataset and train predictive model |
| `POST` | `/model/evaluate` | Evaluate model against held-out split |
| `GET` | `/metrics` | Aggregate regression telemetry and history stats |
