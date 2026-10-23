"""
Unit tests for Change Impact Analysis Service.
Verifies AST symbol extraction, requirement link matching, downstream DAG blast radius propagation,
and truthful disclosure generation.
"""

from pathlib import Path
import pytest
from app.schemas.regression import ChangeType
from app.schemas.requirement import (
    RequirementCategory,
    RequirementItem,
    RequirementPriority,
    RequirementSpecification,
    VerificationState,
)
from app.schemas.verification import (
    ArtifactMetadata,
    FileType,
    LinkOrigin,
    LinkType,
    ProjectIngestionReport,
    TraceabilityLink,
)
from app.services.regression.change_impact import ChangeImpactService


@pytest.fixture
def sample_project():
    return ProjectIngestionReport(
        project_id="PROJ-TEST-001",
        name="Test Math Suite",
        total_files=2,
        total_size_bytes=500,
        detected_manifests=[],
        detected_test_frameworks=["pytest"],
        available_test_commands=["pytest"],
        ingested_artifacts=[
            ArtifactMetadata(
                id="ART-001",
                project_id="PROJ-TEST-001",
                relative_path="calculator.py",
                file_type=FileType.SOURCE_FILE,
                language="python",
                sha256="abc123hash",
                size_bytes=200,
                line_count=15,
                symbols=["add", "subtract"],
                created_at="2026-10-10T00:00:00Z",
            ),
            ArtifactMetadata(
                id="ART-002",
                project_id="PROJ-TEST-001",
                relative_path="tests/test_calculator.py",
                file_type=FileType.TEST_FILE,
                language="python",
                sha256="def456hash",
                size_bytes=300,
                line_count=25,
                symbols=["test_add", "test_subtract"],
                created_at="2026-10-10T00:00:00Z",
            ),
        ],
        warnings=[],
        ingested_at="2026-10-10T00:00:00Z",
    )


@pytest.fixture
def sample_spec():
    req1 = RequirementItem(
        id="REQ-001",
        title="Add Operation",
        category=RequirementCategory.FUNCTIONAL,
        description="Must add two numbers accurately",
        priority=RequirementPriority.CRITICAL,
        is_inferred=False,
        verification_state=VerificationState.UNVERIFIED,
        acceptance_criteria=[],
        assumptions=[],
        depends_on=[],
        refines=[],
    )
    req2 = RequirementItem(
        id="REQ-002",
        title="Audit Logging",
        category=RequirementCategory.NONFUNCTIONAL,
        description="Audit operations",
        priority=RequirementPriority.HIGH,
        is_inferred=True,
        verification_state=VerificationState.UNVERIFIED,
        acceptance_criteria=[],
        assumptions=[],
        depends_on=["REQ-001"],  # REQ-002 depends on REQ-001
        refines=[],
    )
    return RequirementSpecification(
        id="SPEC-TEST-001",
        title="Calculator Spec",
        source_prompt="Build calculator",
        requirements=[req1, req2],
        assumptions=[],
        created_at="2026-10-10T00:00:00Z",
        updated_at="2026-10-10T00:00:00Z",
    )


@pytest.fixture
def sample_links():
    return [
        TraceabilityLink(
            id="LNK-001",
            project_id="PROJ-TEST-001",
            specification_id="SPEC-TEST-001",
            requirement_id="REQ-001",
            artifact_path="calculator.py",
            symbol_name="add",
            link_type=LinkType.CONFIRMED_IMPLEMENTATION,
            link_origin=LinkOrigin.DEVELOPER_CONFIRMATION,
            confidence=1.0,
            is_confirmed=True,
            rationale="Implements add",
            created_at="2026-10-10T00:00:00Z",
        ),
        TraceabilityLink(
            id="LNK-002",
            project_id="PROJ-TEST-001",
            specification_id="SPEC-TEST-001",
            requirement_id="REQ-001",
            artifact_path="tests/test_calculator.py",
            symbol_name="test_add",
            link_type=LinkType.CONFIRMED_TEST,
            link_origin=LinkOrigin.DEVELOPER_CONFIRMATION,
            confidence=1.0,
            is_confirmed=True,
            rationale="Tests add",
            created_at="2026-10-10T00:00:00Z",
        ),
    ]


def test_change_impact_analysis_direct_and_downstream(sample_project, sample_spec, sample_links):
    """Verify change impact maps modified files, extracts symbols, and propagates blast radius."""
    service = ChangeImpactService()

    report = service.analyze_change(
        project=sample_project,
        changed_files=["calculator.py"],
        links=sample_links,
        spec=sample_spec,
    )

    assert report.project_id == "PROJ-TEST-001"
    assert len(report.changed_files) == 1
    assert report.changed_files[0].file_path == "calculator.py"
    assert report.changed_files[0].change_type == ChangeType.MODIFIED
    assert "add" in report.changed_symbols

    # Directly affected requirement
    assert len(report.directly_affected_requirements) == 1
    assert report.directly_affected_requirements[0].requirement_id == "REQ-001"
    assert report.directly_affected_requirements[0].is_directly_changed is True

    # Downstream requirement via DAG
    assert len(report.downstream_affected_requirements) == 1
    assert report.downstream_affected_requirements[0].requirement_id == "REQ-002"

    assert report.affected_tests_candidate_count >= 1
    assert any("Git unified diff" in d for d in report.evidence_disclosures)


def test_change_impact_with_custom_ast_content(sample_project, sample_links):
    """Verify AST symbol extraction from new custom content."""
    service = ChangeImpactService()

    custom_code = "def multiply(a, b):\n    return a * b\nclass AdvancedMath:\n    pass\n"

    report = service.analyze_change(
        project=sample_project,
        changed_files=["calculator.py"],
        links=sample_links,
        file_contents={"calculator.py": custom_code},
    )

    assert "multiply" in report.changed_symbols
    assert "AdvancedMath" in report.changed_symbols
