"""
Unit tests for Test Selection Strategies and Budget Constraints.
Verifies all_tests, impact_based, and predictive selection with top-k and budget cutoffs.
"""

import pytest
from app.schemas.regression import (
    ChangedFileInfo,
    ChangeImpactReport,
    ChangeType,
    PrioritizationStrategy,
)
from app.schemas.verification import (
    ArtifactMetadata,
    FileType,
    ProjectIngestionReport,
)
from app.services.regression.selector import TestSelector


@pytest.fixture
def selector_fixture():
    selector = TestSelector()

    project = ProjectIngestionReport(
        project_id="PROJ-SEL",
        name="Selection Test Project",
        total_files=4,
        total_size_bytes=800,
        ingested_artifacts=[
            ArtifactMetadata(
                id=f"ART-{i}",
                project_id="PROJ-SEL",
                relative_path=f"tests/test_{i}.py",
                file_type=FileType.TEST_FILE,
                language="python",
                sha256=f"hash{i}",
                size_bytes=100,
                line_count=10,
                symbols=[f"test_func_{i}"],
                created_at="2026-10-10T00:00:00Z",
            )
            for i in range(1, 5)
        ],
        ingested_at="2026-10-10T00:00:00Z",
    )

    impact = ChangeImpactReport(
        analysis_id="ANL-SEL",
        project_id="PROJ-SEL",
        changed_files=[
            ChangedFileInfo(
                file_path="tests/test_1.py",
                change_type=ChangeType.MODIFIED,
                changed_symbols=["test_func_1"],
                is_test=True,
            )
        ],
        changed_symbols=["test_func_1"],
        max_blast_radius_depth=0,
        created_at="2026-10-10T00:00:00Z",
    )

    return selector, impact, project


def test_top_k_selection_and_exclusion_reasons(selector_fixture):
    """Verify top_k selects top K and properly explains excluded tests."""
    selector, impact, project = selector_fixture

    res = selector.select_tests(
        impact=impact,
        project=project,
        links=[],
        strategy=PrioritizationStrategy.ALL_TESTS,
        top_k=2,
    )

    assert res.total_tests == 4
    assert res.selected_count == 2
    assert res.excluded_count == 2
    assert len(res.selected_tests) == 2
    assert len(res.excluded_tests) == 2

    # Excluded tests should contain explanation
    for ex in res.excluded_tests:
        assert "Exceeded Top-2" in ex.exclusion_reason
        assert ex.rank > 2


def test_execution_budget_selection(selector_fixture):
    """Verify execution budget halts selection when cumulative duration is exceeded."""
    selector, impact, project = selector_fixture

    # Default duration per test is 50ms, so 75ms budget should allow 1 test
    res = selector.select_tests(
        impact=impact,
        project=project,
        links=[],
        strategy=PrioritizationStrategy.ALL_TESTS,
        execution_budget_ms=75.0,
    )

    assert res.selected_count == 1
    assert res.excluded_count == 3
    assert any("Exceeded execution time budget" in ex.exclusion_reason for ex in res.excluded_tests)
