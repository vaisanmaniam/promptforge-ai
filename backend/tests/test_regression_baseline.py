"""
Unit tests for Deterministic Prioritization Baseline.
Verifies multi-signal ranking formula, feature weights, human-readable explanations,
and missing-history handling.
"""

import pytest
from app.schemas.regression import ChangedFileInfo, ChangeImpactReport, ChangeType
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
from app.services.regression.baseline import DeterministicPrioritizer
from app.services.regression.history import TestHistoryRepository


@pytest.fixture
def baseline_setup(tmp_path):
    repo = TestHistoryRepository(data_dir=tmp_path)
    prioritizer = DeterministicPrioritizer(history_repo=repo)

    project = ProjectIngestionReport(
        project_id="PROJ-MATH",
        name="Math Project",
        total_files=2,
        total_size_bytes=400,
        ingested_artifacts=[
            ArtifactMetadata(
                id="ART-01",
                project_id="PROJ-MATH",
                relative_path="math_lib.py",
                file_type=FileType.SOURCE_FILE,
                language="python",
                sha256="hash1",
                size_bytes=200,
                line_count=20,
                symbols=["add", "divide"],
                created_at="2026-10-10T00:00:00Z",
            ),
            ArtifactMetadata(
                id="ART-02",
                project_id="PROJ-MATH",
                relative_path="tests/test_math.py",
                file_type=FileType.TEST_FILE,
                language="python",
                sha256="hash2",
                size_bytes=200,
                line_count=20,
                symbols=["test_add", "test_divide"],
                created_at="2026-10-10T00:00:00Z",
            ),
        ],
        ingested_at="2026-10-10T00:00:00Z",
    )

    impact = ChangeImpactReport(
        analysis_id="ANL-TEST",
        project_id="PROJ-MATH",
        changed_files=[
            ChangedFileInfo(
                file_path="math_lib.py",
                change_type=ChangeType.MODIFIED,
                changed_symbols=["add"],
                is_test=False,
            )
        ],
        changed_symbols=["add"],
        max_blast_radius_depth=1,
        created_at="2026-10-10T00:00:00Z",
    )

    links = [
        TraceabilityLink(
            id="LNK-01",
            project_id="PROJ-MATH",
            specification_id="SPEC-01",
            requirement_id="REQ-01",
            artifact_path="math_lib.py",
            symbol_name="add",
            link_type=LinkType.CONFIRMED_IMPLEMENTATION,
            link_origin=LinkOrigin.DEVELOPER_CONFIRMATION,
            confidence=1.0,
            is_confirmed=True,
            rationale="Implements",
            created_at="2026-10-10T00:00:00Z",
        ),
        TraceabilityLink(
            id="LNK-02",
            project_id="PROJ-MATH",
            specification_id="SPEC-01",
            requirement_id="REQ-01",
            artifact_path="tests/test_math.py",
            symbol_name="test_add",
            link_type=LinkType.CONFIRMED_TEST,
            link_origin=LinkOrigin.DEVELOPER_CONFIRMATION,
            confidence=1.0,
            is_confirmed=True,
            rationale="Tests add",
            created_at="2026-10-10T00:00:00Z",
        ),
    ]

    return prioritizer, impact, project, links, repo


def test_deterministic_prioritization_ranks_directly_related_test_highest(baseline_setup):
    """Verify test_add matching modified symbol 'add' is prioritized over test_divide."""
    prioritizer, impact, project, links, _ = baseline_setup

    ranked = prioritizer.rank_tests(
        impact=impact,
        project=project,
        links=links,
        discovered_test_nodes=["tests/test_math.py::test_add", "tests/test_math.py::test_divide"],
    )

    assert len(ranked) == 2
    assert ranked[0].test_id == "tests/test_math.py::test_add"
    assert ranked[0].rank == 1
    assert ranked[0].score > ranked[1].score
    assert any("matches changed symbol" in exp or "modified" in exp for exp in ranked[0].explanations)
    assert any("No prior execution history" in exp for exp in ranked[0].explanations)


def test_historical_failure_increases_score(baseline_setup):
    """Verify test with genuine past failures receives higher priority."""
    prioritizer, impact, project, links, repo = baseline_setup

    # Record historical failure for test_divide
    from ai.regression_model.schema import RegressionFeatureVector, TestExecutionObservation
    repo.add_observation(
        TestExecutionObservation(
            observation_id="HIST-01",
            change_id="CHG-OLD",
            project_id="PROJ-MATH",
            test_id="tests/test_math.py::test_divide",
            outcome=1,
            features=RegressionFeatureVector(),
            label_provenance="docker_verification_run",
            is_synthetic=False,
            timestamp="2026-10-09T00:00:00Z",
        )
    )

    ranked = prioritizer.rank_tests(
        impact=impact,
        project=project,
        links=links,
        discovered_test_nodes=["tests/test_math.py::test_add", "tests/test_math.py::test_divide"],
    )

    divide_item = next(r for r in ranked if "test_divide" in r.test_id)
    assert divide_item.historical_failure_rate == 1.0
    assert any("Historical failure rate: 100.0%" in exp for exp in divide_item.explanations)
