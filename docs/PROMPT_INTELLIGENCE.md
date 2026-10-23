# PromptForge AI: Prompt Intelligence Engine Specification

## 1. Engine Overview

The **Prompt Intelligence Engine** is the first operational AI/ML subsystem of PromptForge AI. It analyzes developer prompts, classifies software engineering intent, detects information gaps, scores prompt quality on a transparent 0–100 scale, and restructures prompts into verifiable engineering specifications.

---

## 2. Task Category Classification

The platform categorizes natural-language requests into 8 discrete software engineering task categories:

| Task Category | Scope & Description |
| :--- | :--- |
| **`code_generation`** | Algorithm implementation, classes, functions, data structures, and utilities. |
| **`debugging`** | Root cause analysis, exception handling, crash resolution, and bug fixes. |
| **`code_review`** | Code smell detection, security audits, SOLID principles, and PR reviews. |
| **`api_development`** | REST endpoints, GraphQL queries/mutations, WebSockets, gRPC, and controllers. |
| **`sql_generation`** | Queries, DDL migrations, window functions, CTEs, and query optimization. |
| **`test_generation`** | Unit tests, mock suites, integration tests, fuzzing, and benchmark suites. |
| **`documentation`** | Docstrings, Markdown specifications, ADRs, READMEs, and API references. |
| **`devops`** | Dockerfiles, Kubernetes manifests, CI/CD pipelines, Terraform, and system services. |

### Classification Architecture
* **Primary ML Pipeline**: TF-IDF Vectorizer (word and char n-grams 1-2, sublinear TF) + Multinomial Logistic Regression (`C=1.5`, balanced class weights).
* **Deterministic Fallback**: Keyword and regex matcher with uniform prior fallback for cold-start environments.
* **Model Provenance**: Artifact stored at `ai/models/prompt_classifier_v1.joblib` with metadata companion `ai/models/prompt_classifier_v1_metadata.json`.

---

## 3. Component & Information Gap Detection

Prompts are analyzed for 10 critical software engineering dimensions:

1. **`objective`**: Core goal or required capability.
2. **`context`**: Operational environment, architecture, existing codebase, or problem background.
3. **`target_technology`**: Programming language, framework, database, or runtime environment.
4. **`inputs`**: Function arguments, request payloads, schemas, or query parameters.
5. **`expected_outputs`**: Return types, serialization formats, or HTTP response status codes.
6. **`functional_requirements`**: Explicit logic, algorithms, transformation steps, or business rules.
7. **`constraints`**: Time/space complexity (e.g., $O(1)$), memory budgets, timeouts, or thread-safety.
8. **`security_requirements`**: Authentication, password hashing, authorization, sanitization, or encryption.
9. **`testing_requirements`**: Test cases, test frameworks (pytest, Jest), mocking, or assertions.
10. **`acceptance_criteria`**: Verifiable conditions for task completion or exception behavior.

---

## 4. Deterministic Quality Scoring Formula

Prompt quality is evaluated on a transparent **0–100 scale** using 6 validated dimensions:

$$\text{Overall Score} = \sum_{d \in \text{Dimensions}} \text{Weight}_d \times \text{Score}_d$$

### Configured Weights

| Dimension | Weight | Primary Criteria |
| :--- | :--- | :--- |
| **Clarity** | **20%** | Clear, direct phrasing; structured markdown lists/code blocks; penalizes ambiguous qualifiers. |
| **Context** | **15%** | Architecture background, existing service context, and operational scenario. |
| **Specificity** | **20%** | Explicit target technology, named libraries, concrete data types, and parameter names. |
| **Constraints** | **15%** | Performance budgets, time/space complexity, resource limits, and error handling rules. |
| **Output Definition** | **15%** | Concrete return signatures, schemas, status codes, and serialization formats. |
| **Completeness** | **15%** | Ratio of core software engineering components present vs missing. |

---

## 5. Ambiguity Detection & Clarification

The ambiguity detector flags open-ended or subjective qualifiers:
* **Subjective Metrics**: "fast", "scalable", "bulletproof" (lacks latency SLAs or concurrency targets).
* **Open-Ended Scope**: "etc.", "and so on", "and more" (creates unchecked scope creep).
* **Vague Quality Claims**: "good", "proper", "reasonable" (lacks measurable acceptance criteria).
* **Unconstrained Decisions**: "any database", "whichever framework" (delegates architecture to inference).

For each flagged term, the engine generates an actionable **clarification question**.

---

## 6. Prompt Optimizer & Assumption Disclosure

The prompt optimizer restructures inputs into standardized software engineering prompts:
1. **Preserves Developer Intent**: Original prompt is kept verbatim under `### 1. Objective`.
2. **Injects Structure**: Adds standardized headings for Context, Functional Specs, Contract, Constraints, and Verification.
3. **Exposes Proposed Assumptions**: Unspecified choices (e.g. framework, database) are generated as explicit proposals labeled `[PROPOSED ASSUMPTION - Requires Confirmation]`.
4. **Prevents Silent Hallucination**: Assumptions are never presented as user-confirmed facts.

---

## 7. Token-Efficiency Analysis

Token counting distinguishes between exact tokenization and heuristic estimates:
* **Exact Method (`exact_bpe`)**: Uses `tiktoken` with `cl100k_base` encoding.
* **Heuristic Method (`heuristic_estimate`)**: Blended character-to-word ratio when BPE runtime is unavailable.
* **Supplementary Metric**: Quality Score per Token ($\text{QPT} = \frac{\text{Score}}{\text{Tokens}} \times 100$).
