"""
Deterministic and Explainable Requirement Extractor.
Transforms natural language prompts and Phase 2 component intelligence into
formally structured, verifiable software requirements with explicit acceptance criteria
and transparent assumption labeling.
"""

import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.schemas.requirement import (
    AcceptanceCriterion,
    AssumptionItem,
    AssumptionStatus,
    RequirementCategory,
    RequirementItem,
    RequirementPriority,
    RequirementSpecification,
    RequirementStatus,
    VerificationState,
    VerificationType,
)
from ai.prompt_classifier.model import SklearnPromptClassifier
from app.services.prompt_intelligence.ambiguity import AmbiguityDetector
from app.services.prompt_intelligence.components import ComponentDetector
from app.services.prompt_intelligence.optimizer import PromptOptimizer


class RequirementExtractor:
    """
    Extracts structured requirements from software prompts deterministically.
    Clearly distinguishes explicit user statements from inferred architecture assumptions.
    """

    def __init__(self):
        self.classifier = SklearnPromptClassifier()
        self.component_detector = ComponentDetector()
        self.ambiguity_detector = AmbiguityDetector()
        self.prompt_optimizer = PromptOptimizer()

    def extract(
        self,
        prompt: str,
        task_category: Optional[str] = None,
        spec_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> RequirementSpecification:
        """
        Extract a complete requirement specification from a prompt.
        """
        spec_id = spec_id or f"spec-{uuid.uuid4().hex[:12]}"
        prompt_text = prompt.strip()

        # Step 1: Detect category, software components, and optimization insights
        if task_category:
            effective_category = task_category
        else:
            clf_result = self.classifier.predict(prompt_text)
            effective_category = clf_result.predicted_category

        component_report = self.component_detector.analyze(prompt_text)
        ambiguity_report = self.ambiguity_detector.analyze(prompt_text)

        opt_result = self.prompt_optimizer.optimize(
            prompt=prompt_text,
            task_category=effective_category,
            comp_report=component_report,
            amb_report=ambiguity_report,
        )

        # Step 2: Generate title if not supplied
        spec_title = title or self._derive_title(prompt_text, effective_category)

        # Step 3: Segment prompt clauses and detect explicit requirements
        req_counter = 1
        ac_counter = 1
        asm_counter = 1

        requirements: List[RequirementItem] = []
        global_assumptions: List[AssumptionItem] = []

        # Convert optimizer proposed assumptions into formal AssumptionItems
        for opt_asm in opt_result.assumptions:
            asm_id = f"ASM-{asm_counter:03d}"
            asm_counter += 1
            global_assumptions.append(
                AssumptionItem(
                    id=asm_id,
                    text=opt_asm,
                    source_component="prompt_optimization",
                    status=AssumptionStatus.UNRESOLVED,
                    impact="high" if "stack" in opt_asm.lower() or "auth" in opt_asm.lower() else "medium",
                )
            )

        # --- A. FUNCTIONAL REQUIREMENTS ---
        # 1. Primary Objective Requirement
        primary_req, ac_counter = self._build_primary_objective_requirement(
            prompt_text=prompt_text,
            task_category=effective_category,
            component_report=component_report,
            req_id=f"REQ-{req_counter:03d}",
            ac_start_id=ac_counter,
        )
        requirements.append(primary_req)
        req_counter += 1

        # 2. Extract specific functional sub-clauses
        sub_functional_reqs, req_counter, ac_counter = self._extract_sub_functional(
            prompt_text=prompt_text,
            component_report=component_report,
            req_counter=req_counter,
            ac_counter=ac_counter,
            parent_req_id=primary_req.id,
        )
        requirements.extend(sub_functional_reqs)

        # --- B. TECHNICAL CONSTRAINTS ---
        constraint_reqs, req_counter, ac_counter = self._extract_constraints(
            prompt_text=prompt_text,
            component_report=component_report,
            opt_result=opt_result,
            req_counter=req_counter,
            ac_counter=ac_counter,
        )
        requirements.extend(constraint_reqs)

        # --- C. NON-FUNCTIONAL REQUIREMENTS ---
        nfr_reqs, req_counter, ac_counter, nfr_asms, asm_counter = self._extract_nonfunctional(
            prompt_text=prompt_text,
            component_report=component_report,
            req_counter=req_counter,
            ac_counter=ac_counter,
            asm_counter=asm_counter,
        )
        requirements.extend(nfr_reqs)
        global_assumptions.extend(nfr_asms)

        # --- D. SECURITY REQUIREMENTS ---
        sec_reqs, req_counter, ac_counter, sec_asms, asm_counter = self._extract_security(
            prompt_text=prompt_text,
            component_report=component_report,
            req_counter=req_counter,
            ac_counter=ac_counter,
            asm_counter=asm_counter,
        )
        requirements.extend(sec_reqs)
        global_assumptions.extend(sec_asms)

        # Step 4: Compute category breakdown
        breakdown: Dict[str, int] = {
            RequirementCategory.FUNCTIONAL.value: 0,
            RequirementCategory.NONFUNCTIONAL.value: 0,
            RequirementCategory.TECHNICAL_CONSTRAINT.value: 0,
            RequirementCategory.SECURITY.value: 0,
        }
        for r in requirements:
            breakdown[r.category.value] = breakdown.get(r.category.value, 0) + 1

        now_iso = datetime.utcnow().isoformat() + "Z"

        return RequirementSpecification(
            id=spec_id,
            title=spec_title,
            source_prompt=prompt_text,
            task_category=effective_category,
            category_breakdown=breakdown,
            requirements=requirements,
            assumptions=global_assumptions,
            created_at=now_iso,
            updated_at=now_iso,
            version=1,
        )

    def _derive_title(self, prompt: str, category: str) -> str:
        """Derives a readable specification title from prompt essence."""
        first_line = prompt.strip().split("\n")[0]
        cleaned = re.sub(r"^(implement|write|create|build|develop|generate|design)\s+", "", first_line, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"[^\w\s-]", "", cleaned)
        if len(cleaned) > 50:
            cleaned = cleaned[:47].rsplit(" ", 1)[0] + "..."
        cat_prefix = category.replace("_", " ").title()
        return f"{cat_prefix}: {cleaned.title()}" if cleaned else f"{cat_prefix} Specification"

    def _build_primary_objective_requirement(
        self,
        prompt_text: str,
        task_category: str,
        component_report,
        req_id: str,
        ac_start_id: int,
    ) -> Tuple[RequirementItem, int]:
        """Creates the primary functional requirement from prompt objective."""
        first_sentence = re.split(r"[.!?\n]", prompt_text)[0].strip()
        evidence = component_report.findings.get("objective", {}).evidence if hasattr(component_report, "findings") else None

        title = f"Core Objective Implementation ({task_category.replace('_', ' ').title()})"
        description = (
            f"Implement primary capability specified in prompt: '{first_sentence}'."
            f" Must satisfy all requested operations and behavioral contracts."
        )

        ac_id1 = f"AC-{ac_start_id:03d}"
        ac_id2 = f"AC-{ac_start_id + 1:03d}"
        ac_next = ac_start_id + 2

        criteria = [
            AcceptanceCriterion(
                id=ac_id1,
                description=f"Primary functional capability '{first_sentence}' executes successfully under standard inputs.",
                verification_type=VerificationType.UNIT_TEST,
                status="pending",
            ),
            AcceptanceCriterion(
                id=ac_id2,
                description="Invalid or boundary inputs produce explicit, documented error responses without unhandled crashes.",
                verification_type=VerificationType.UNIT_TEST,
                status="pending",
            ),
        ]

        item = RequirementItem(
            id=req_id,
            title=title,
            description=description,
            category=RequirementCategory.FUNCTIONAL,
            priority=RequirementPriority.CRITICAL,
            status=RequirementStatus.EXPLICIT,
            source_text=evidence or first_sentence,
            acceptance_criteria=criteria,
            verification_state=VerificationState.UNVERIFIED,
            depends_on=[],
            refines=[],
        )
        return item, ac_next

    def _extract_sub_functional(
        self,
        prompt_text: str,
        component_report,
        req_counter: int,
        ac_counter: int,
        parent_req_id: str,
    ) -> Tuple[List[RequirementItem], int, int]:
        """Extracts secondary functional actions (e.g. verbs, bullet items, inputs/outputs)."""
        items: List[RequirementItem] = []

        # Check for inputs and outputs specification
        inputs_ev = getattr(component_report.findings.get("inputs"), "evidence", None) if hasattr(component_report, "findings") else None
        outputs_ev = getattr(component_report.findings.get("expected_outputs"), "evidence", None) if hasattr(component_report, "findings") else None

        if inputs_ev or outputs_ev:
            req_id = f"REQ-{req_counter:03d}"
            req_counter += 1
            ac_id = f"AC-{ac_counter:03d}"
            ac_counter += 1

            desc_parts = []
            if inputs_ev:
                desc_parts.append(f"Accepts and validates input schema: {inputs_ev}.")
            if outputs_ev:
                desc_parts.append(f"Returns expected output format: {outputs_ev}.")

            items.append(
                RequirementItem(
                    id=req_id,
                    title="Data Contract & I/O Schema Validation",
                    description=" ".join(desc_parts),
                    category=RequirementCategory.FUNCTIONAL,
                    priority=RequirementPriority.HIGH,
                    status=RequirementStatus.EXPLICIT,
                    source_text=f"{inputs_ev or ''} {outputs_ev or ''}".strip(),
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id=ac_id,
                            description="All incoming payloads are strictly validated against the target schema and rejected if malformed.",
                            verification_type=VerificationType.UNIT_TEST,
                            status="pending",
                        )
                    ],
                    depends_on=[parent_req_id],
                )
            )

        # Check for clauses matching specific operations like cache eviction, CRUD, pagination, filtering
        clause_patterns = [
            (r"\b(cache|evict|expiry|ttl|lru|lfu)\b", "Cache State & Eviction Policy", "Implement predictable cache lifecycle, eviction algorithm, and TTL expiration."),
            (r"\b(pagination|page\s+size|offset|cursor)\b", "Pagination & Result Windowing", "Support bounded page sizing and cursor/offset retrieval."),
            (r"\b(filter|sort|search|query)\b", "Data Filtering & Query Capabilities", "Provide structured filtering and sorting parameters."),
            (r"\b(concurrency|lock|thread-safe|mutex|race\s+condition)\b", "Thread Safety & Concurrency Control", "Guarantee atomicity and prevent race conditions under parallel execution."),
        ]

        prompt_lower = prompt_text.lower()
        for pattern, title, desc in clause_patterns:
            if re.search(pattern, prompt_lower):
                req_id = f"REQ-{req_counter:03d}"
                req_counter += 1
                ac_id = f"AC-{ac_counter:03d}"
                ac_counter += 1
                items.append(
                    RequirementItem(
                        id=req_id,
                        title=title,
                        description=desc,
                        category=RequirementCategory.FUNCTIONAL,
                        priority=RequirementPriority.HIGH,
                        status=RequirementStatus.EXPLICIT,
                        source_text=f"Detected pattern '{pattern}' in prompt",
                        acceptance_criteria=[
                            AcceptanceCriterion(
                                id=ac_id,
                                description=f"Functional verification test demonstrates {title.lower()} under simulated workload.",
                                verification_type=VerificationType.UNIT_TEST,
                                status="pending",
                            )
                        ],
                        depends_on=[parent_req_id],
                    )
                )

        return items, req_counter, ac_counter

    def _extract_constraints(
        self,
        prompt_text: str,
        component_report,
        opt_result,
        req_counter: int,
        ac_counter: int,
    ) -> Tuple[List[RequirementItem], int, int]:
        """Extracts technical constraints (runtime, algorithms, memory, frameworks)."""
        items: List[RequirementItem] = []

        # 1. Target Technology Constraint
        tech_ev = getattr(component_report.findings.get("target_technology"), "evidence", None) if hasattr(component_report, "findings") else None
        req_id = f"REQ-{req_counter:03d}"
        req_counter += 1
        ac_id = f"AC-{ac_counter:03d}"
        ac_counter += 1

        if tech_ev:
            title = f"Technology Stack: {tech_ev.strip()}"
            desc = f"Implementation must utilize the specified tech stack: {tech_ev}."
            status = RequirementStatus.EXPLICIT
            source = tech_ev
        else:
            default_tech = getattr(opt_result, "task_category", "standard library")
            title = "Default Execution Environment & Runtime"
            desc = f"Target runtime environment standard baseline for {default_tech}."
            status = RequirementStatus.INFERRED
            source = "Inferred runtime baseline"

        items.append(
            RequirementItem(
                id=req_id,
                title=title,
                description=desc,
                category=RequirementCategory.TECHNICAL_CONSTRAINT,
                priority=RequirementPriority.HIGH,
                status=status,
                source_text=source,
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id=ac_id,
                        description="Code compiles and runs on the declared target runtime without missing import errors.",
                        verification_type=VerificationType.STATIC_ANALYSIS,
                        status="pending",
                    )
                ],
                depends_on=[],
            )
        )

        # 2. Algorithmic / Complexity Constraints
        constraints_ev = getattr(component_report.findings.get("constraints"), "evidence", None) if hasattr(component_report, "findings") else None
        if constraints_ev or re.search(r"\bo\(\d|n|log\s*n\)", prompt_text, flags=re.IGNORECASE):
            req_id2 = f"REQ-{req_counter:03d}"
            req_counter += 1
            ac_id2 = f"AC-{ac_counter:03d}"
            ac_counter += 1
            items.append(
                RequirementItem(
                    id=req_id2,
                    title="Computational Complexity & Resource Bounds",
                    description=f"Algorithm must satisfy strict computational and space constraints: {constraints_ev or 'bounded complexity'}.",
                    category=RequirementCategory.TECHNICAL_CONSTRAINT,
                    priority=RequirementPriority.HIGH,
                    status=RequirementStatus.EXPLICIT,
                    source_text=constraints_ev or "Prompt asymptotic complexity constraint",
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id=ac_id2,
                            description="Benchmark execution confirms operations satisfy specified complexity limits.",
                            verification_type=VerificationType.UNIT_TEST,
                            status="pending",
                        )
                    ],
                    depends_on=[],
                )
            )

        return items, req_counter, ac_counter

    def _extract_nonfunctional(
        self,
        prompt_text: str,
        component_report,
        req_counter: int,
        ac_counter: int,
        asm_counter: int,
    ) -> Tuple[List[RequirementItem], int, int, List[AssumptionItem], int]:
        """Extracts nonfunctional requirements (latency, reliability, thread-safety)."""
        items: List[RequirementItem] = []
        asms: List[AssumptionItem] = []

        prompt_lower = prompt_text.lower()
        has_perf = any(kw in prompt_lower for kw in ["latency", "throughput", "fast", "performance", "speed", "under "])

        req_id = f"REQ-{req_counter:03d}"
        req_counter += 1
        ac_id = f"AC-{ac_counter:03d}"
        ac_counter += 1

        if has_perf:
            items.append(
                RequirementItem(
                    id=req_id,
                    title="Latency & Execution Performance",
                    description="System must execute operations with bounded latency and minimal overhead under normal operational load.",
                    category=RequirementCategory.NONFUNCTIONAL,
                    priority=RequirementPriority.MEDIUM,
                    status=RequirementStatus.EXPLICIT,
                    source_text="Performance keywords detected in prompt",
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id=ac_id,
                            description="Performance regression tests confirm 95th percentile latency remains within acceptable thresholds.",
                            verification_type=VerificationType.UNIT_TEST,
                            status="pending",
                        )
                    ],
                )
            )
        else:
            # Inferred baseline reliability requirement
            asm_id = f"ASM-{asm_counter:03d}"
            asm_counter += 1
            asm_item = AssumptionItem(
                id=asm_id,
                text="Standard operational response time (< 500ms for I/O, < 50ms for in-memory) assumed as nonfunctional baseline.",
                source_component="nonfunctional_inference",
                status=AssumptionStatus.UNRESOLVED,
                impact="low",
            )
            asms.append(asm_item)

            items.append(
                RequirementItem(
                    id=req_id,
                    title="Baseline Operational Reliability & Error Bounding",
                    description="Standard error bounding and graceful degradation under abnormal operational conditions.",
                    category=RequirementCategory.NONFUNCTIONAL,
                    priority=RequirementPriority.LOW,
                    status=RequirementStatus.INFERRED,
                    source_text="Baseline software engineering reliability requirement",
                    assumptions=[asm_item],
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id=ac_id,
                            description="Unhandlable internal exceptions are captured and wrapped with structured domain error types.",
                            verification_type=VerificationType.UNIT_TEST,
                            status="pending",
                        )
                    ],
                )
            )

        return items, req_counter, ac_counter, asms, asm_counter

    def _extract_security(
        self,
        prompt_text: str,
        component_report,
        req_counter: int,
        ac_counter: int,
        asm_counter: int,
    ) -> Tuple[List[RequirementItem], int, int, List[AssumptionItem], int]:
        """Extracts security requirements (authentication, input sanitization, rate limiting)."""
        items: List[RequirementItem] = []
        asms: List[AssumptionItem] = []

        sec_ev = getattr(component_report.findings.get("security_requirements"), "evidence", None) if hasattr(component_report, "findings") else None
        prompt_lower = prompt_text.lower()
        has_auth = any(kw in prompt_lower for kw in ["auth", "jwt", "token", "password", "hash", "secret", "oauth"])

        req_id = f"REQ-{req_counter:03d}"
        req_counter += 1
        ac_id = f"AC-{ac_counter:03d}"
        ac_counter += 1

        if sec_ev or has_auth:
            items.append(
                RequirementItem(
                    id=req_id,
                    title="Security: Identity, Authentication & Cryptographic Protection",
                    description=f"Enforce secure credential handling, token verification, and cryptographic controls: {sec_ev or 'Standard security defenses'}.",
                    category=RequirementCategory.SECURITY,
                    priority=RequirementPriority.CRITICAL,
                    status=RequirementStatus.EXPLICIT,
                    source_text=sec_ev or "Security keywords in prompt",
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id=ac_id,
                            description="Unauthenticated requests or tampered tokens are rejected with 401 Unauthorized / appropriate error code.",
                            verification_type=VerificationType.UNIT_TEST,
                            status="pending",
                        )
                    ],
                )
            )
        else:
            # Inferred security: Input Sanitization & Attack Prevention
            asm_id = f"ASM-{asm_counter:03d}"
            asm_counter += 1
            asm_item = AssumptionItem(
                id=asm_id,
                text="Inferred baseline security: strict input validation and injection prevention (OWASP Top 10) apply by default.",
                source_component="security_inference",
                status=AssumptionStatus.UNRESOLVED,
                impact="medium",
            )
            asms.append(asm_item)

            items.append(
                RequirementItem(
                    id=req_id,
                    title="Security Baseline: Input Sanitization & Injection Defense",
                    description="Sanitize all untrusted inputs to prevent code, SQL, or command injection vulnerabilities.",
                    category=RequirementCategory.SECURITY,
                    priority=RequirementPriority.HIGH,
                    status=RequirementStatus.INFERRED,
                    source_text="Default defensive engineering baseline",
                    assumptions=[asm_item],
                    acceptance_criteria=[
                        AcceptanceCriterion(
                            id=ac_id,
                            description="Malformed, injection-prone, or oversized payloads fail schema validation cleanly.",
                            verification_type=VerificationType.UNIT_TEST,
                            status="pending",
                        )
                    ],
                )
            )

        return items, req_counter, ac_counter, asms, asm_counter
