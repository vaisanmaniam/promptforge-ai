"""
Unit tests for Requirement Intelligence and Traceability Engine components.
Tests RequirementExtractor, RequirementValidator, TraceabilityGraphEngine,
CoverageAnalyzer, and RequirementRepository.
"""

import pytest
from app.schemas.requirement import (
    AcceptanceCriterion,
    AssumptionItem,
    AssumptionStatus,
    RequirementCategory,
    RequirementItem,
    RequirementPriority,
    RequirementSpecification,
    RequirementStatus,
    VerificationType,
)
from app.services.requirement_intelligence import (
    CoverageAnalyzer,
    RequirementExtractor,
    RequirementRepository,
    RequirementValidator,
    TraceabilityGraphEngine,
)


def test_requirement_extractor_structure():
    """Verify deterministic extraction produces all 4 categories and stable IDs."""
    extractor = RequirementExtractor()
    prompt = (
        "Build a rate-limited REST API in FastAPI using Python 3.11 with Redis caching, "
        "JWT authentication, and O(1) cache lookups."
    )
    spec = extractor.extract(prompt, task_category="api_development")

    assert spec.id.startswith("spec-")
    assert len(spec.requirements) >= 4

    # Verify categories present
    categories = {r.category.value for r in spec.requirements}
    assert RequirementCategory.FUNCTIONAL.value in categories
    assert RequirementCategory.TECHNICAL_CONSTRAINT.value in categories
    assert RequirementCategory.NONFUNCTIONAL.value in categories
    assert RequirementCategory.SECURITY.value in categories

    # Verify stable IDs
    req_ids = [r.id for r in spec.requirements]
    assert "REQ-001" in req_ids
    assert "REQ-002" in req_ids

    # Verify acceptance criteria exist on every extracted item
    for req in spec.requirements:
        assert len(req.acceptance_criteria) > 0
        for ac in req.acceptance_criteria:
            assert ac.id.startswith("AC-")
            assert len(ac.description) > 5

    # Verify explicit vs inferred distinction
    explicit_items = [r for r in spec.requirements if r.status == RequirementStatus.EXPLICIT]
    assert len(explicit_items) > 0


def test_requirement_validator_vague_qualifiers():
    """Verify validator flags vague words lacking quantitative limits."""
    validator = RequirementValidator()

    # Vague item without quantitative threshold
    vague_item = RequirementItem(
        id="REQ-001",
        title="Fast Cache",
        description="The system must be very fast and scalable etc.",
        category=RequirementCategory.NONFUNCTIONAL,
        priority=RequirementPriority.MEDIUM,
        status=RequirementStatus.EXPLICIT,
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-001",
                description="Make sure it runs fast.",
                verification_type=VerificationType.UNIT_TEST,
            )
        ],
    )

    spec = RequirementSpecification(
        id="spec-test-1",
        title="Test Spec",
        source_prompt="Make it fast and scalable etc.",
        requirements=[vague_item],
        assumptions=[],
        created_at="2026-10-09T00:00:00Z",
        updated_at="2026-10-09T00:00:00Z",
    )

    report = validator.validate(spec)
    assert any(f.rule_id == "VAGUE_QUALIFIER" for f in report.findings)


def test_requirement_validator_missing_ac():
    """Verify validator flags requirements lacking acceptance criteria."""
    validator = RequirementValidator()

    no_ac_item = RequirementItem(
        id="REQ-001",
        title="Unverified Feature",
        description="Feature without any testable criteria.",
        category=RequirementCategory.FUNCTIONAL,
        priority=RequirementPriority.HIGH,
        status=RequirementStatus.EXPLICIT,
        acceptance_criteria=[],
    )

    spec = RequirementSpecification(
        id="spec-test-2",
        title="Test Spec",
        source_prompt="Feature without criteria.",
        requirements=[no_ac_item],
        assumptions=[],
        created_at="2026-10-09T00:00:00Z",
        updated_at="2026-10-09T00:00:00Z",
    )

    report = validator.validate(spec)
    assert report.is_valid is False
    assert any(f.rule_id == "MISSING_ACCEPTANCE_CRITERIA" for f in report.findings)


def test_requirement_validator_contradiction():
    """Verify validator detects contradictory architectural requirements."""
    validator = RequirementValidator()

    spec = RequirementSpecification(
        id="spec-test-3",
        title="Contradictory Spec",
        source_prompt="Pure standard library only without third-party packages. Must use FastAPI and Docker.",
        requirements=[
            RequirementItem(
                id="REQ-001",
                title="FastAPI Web Framework",
                description="Use FastAPI framework.",
                category=RequirementCategory.TECHNICAL_CONSTRAINT,
                priority=RequirementPriority.HIGH,
                acceptance_criteria=[
                    AcceptanceCriterion(id="AC-001", description="FastAPI app runs.")
                ],
            )
        ],
        assumptions=[],
        created_at="2026-10-09T00:00:00Z",
        updated_at="2026-10-09T00:00:00Z",
    )

    report = validator.validate(spec)
    assert any(f.rule_id == "CONSTRAINTS_CONFLICT" for f in report.findings)


def test_traceability_graph_networkx_engine():
    """Verify NetworkX directed graph generation, dependency edges, and impact analysis."""
    engine = TraceabilityGraphEngine()

    req1 = RequirementItem(
        id="REQ-001",
        title="Authentication Gateway",
        description="JWT Auth",
        category=RequirementCategory.SECURITY,
        priority=RequirementPriority.CRITICAL,
        acceptance_criteria=[AcceptanceCriterion(id="AC-001", description="Validates JWT.")],
        depends_on=[],
    )
    req2 = RequirementItem(
        id="REQ-002",
        title="User Profile Endpoint",
        description="Protected profile",
        category=RequirementCategory.FUNCTIONAL,
        priority=RequirementPriority.HIGH,
        acceptance_criteria=[AcceptanceCriterion(id="AC-002", description="Returns user profile.")],
        depends_on=["REQ-001"],  # REQ-002 depends on REQ-001
    )
    req3 = RequirementItem(
        id="REQ-003",
        title="Profile Avatar Upload",
        description="Upload avatar",
        category=RequirementCategory.FUNCTIONAL,
        priority=RequirementPriority.MEDIUM,
        acceptance_criteria=[AcceptanceCriterion(id="AC-003", description="Uploads PNG.")],
        depends_on=["REQ-002"],  # REQ-003 depends on REQ-002
    )

    spec = RequirementSpecification(
        id="spec-test-graph",
        title="Traceability Graph Spec",
        source_prompt="Build protected user endpoints.",
        requirements=[req1, req2, req3],
        assumptions=[],
        created_at="2026-10-09T00:00:00Z",
        updated_at="2026-10-09T00:00:00Z",
    )

    graph_payload = engine.export_graph(spec)
    assert len(graph_payload.nodes) == 4  # PROMPT-ROOT + 3 requirements
    assert graph_payload.has_cycles is False

    # Check blast radius impact on REQ-001 (auth gateway)
    # Both REQ-002 and REQ-003 depend on REQ-001
    impact_r1 = engine.analyze_impact(spec, "REQ-001")
    assert "REQ-002" in impact_r1.downstream_dependents
    assert "REQ-003" in impact_r1.downstream_dependents
    assert impact_r1.impact_depth >= 2
    assert impact_r1.risk_level in ("high", "critical")

    # Check impact on REQ-003 (leaf node)
    impact_r3 = engine.analyze_impact(spec, "REQ-003")
    assert len(impact_r3.downstream_dependents) == 0
    assert "REQ-002" in impact_r3.upstream_dependencies
    assert "REQ-001" in impact_r3.upstream_dependencies


def test_coverage_analyzer_truthful_metrics():
    """Verify honest reporting of coverage metrics without fake test runs."""
    analyzer = CoverageAnalyzer()

    asm1 = AssumptionItem(
        id="ASM-001",
        text="Assumed PostgreSQL 16 dialect",
        source_component="tech",
        status=AssumptionStatus.CONFIRMED,
    )
    asm2 = AssumptionItem(
        id="ASM-002",
        text="Assumed 500ms max timeout",
        source_component="nfr",
        status=AssumptionStatus.UNRESOLVED,
    )

    req = RequirementItem(
        id="REQ-001",
        title="API Endpoint",
        description="Endpoint",
        category=RequirementCategory.FUNCTIONAL,
        priority=RequirementPriority.MEDIUM,
        status=RequirementStatus.EXPLICIT,
        acceptance_criteria=[AcceptanceCriterion(id="AC-001", description="Returns 200.")],
    )

    spec = RequirementSpecification(
        id="spec-cov",
        title="Coverage Spec",
        source_prompt="Endpoint test",
        requirements=[req],
        assumptions=[asm1, asm2],
        created_at="2026-10-09T00:00:00Z",
        updated_at="2026-10-09T00:00:00Z",
    )

    report = analyzer.analyze(spec)
    assert report.total_requirements == 1
    assert report.explicit_count == 1
    assert report.inferred_count == 0
    assert report.prompt_coverage_pct == 100.0
    assert report.acceptance_criteria_coverage_pct == 100.0
    assert report.assumption_resolution_pct == 50.0  # 1 of 2 confirmed
    assert report.code_traceability_status == "pending_phase_4"
    assert report.test_traceability_status == "pending_phase_4"


@pytest.mark.asyncio
async def test_requirement_repository_local_storage(tmp_path):
    """Verify repository persists to disk and reloads accurately."""
    repo = RequirementRepository(storage_dir=tmp_path)

    extractor = RequirementExtractor()
    spec = extractor.extract("Implement an asynchronous LRU cache in Python 3.11 with O(1) get/set.")

    saved = await repo.save_specification(spec)
    assert saved.id == spec.id

    loaded = await repo.get_specification(spec.id)
    assert loaded is not None
    assert loaded.id == spec.id
    assert len(loaded.requirements) == len(spec.requirements)

    summaries = await repo.list_specifications()
    assert len(summaries) >= 1
    assert any(s.id == spec.id for s in summaries)
