"""
Unit tests for Code and Requirement Traceability Linking Service.
Tests AST symbol matching, explicit REQ-ID matching, and candidate-to-confirmed workflow.
"""

from pathlib import Path
from app.schemas.requirement import (
    AcceptanceCriterion,
    RequirementCategory,
    RequirementItem,
    RequirementSpecification,
)
from app.schemas.verification import (
    ArtifactMetadata,
    FileType,
    LinkOrigin,
    LinkType,
)
from app.services.verification.traceability import CodeTraceabilityService


def test_traceability_linking_and_confirmation(tmp_path):
    """Verify deterministic link generation via AST symbols and explicit REQ markers."""
    svc = CodeTraceabilityService()

    # Create dummy source and test files
    src_file = tmp_path / "cache.py"
    src_file.write_text(
        "class LRUCache:\n"
        "    # Implements REQ-001\n"
        "    def get(self, key):\n"
        "        return None\n"
        "    def put(self, key, value):\n"
        "        pass\n"
    )

    test_file = tmp_path / "test_cache.py"
    test_file.write_text(
        "from cache import LRUCache\n"
        "def test_req_001_cache_eviction():\n"
        "    c = LRUCache()\n"
        "    assert c.get('missing') is None\n"
    )

    artifacts = [
        ArtifactMetadata(
            id="ART-001",
            project_id="prj-test",
            relative_path="cache.py",
            file_type=FileType.SOURCE_FILE,
            language="python",
            sha256="abc",
            size_bytes=100,
            line_count=7,
            symbols=["class:LRUCache", "method:LRUCache.get", "method:LRUCache.put"],
            created_at="2026-10-10T00:00:00Z",
        ),
        ArtifactMetadata(
            id="ART-002",
            project_id="prj-test",
            relative_path="test_cache.py",
            file_type=FileType.TEST_FILE,
            language="python",
            sha256="def",
            size_bytes=80,
            line_count=5,
            symbols=["def:test_req_001_cache_eviction"],
            created_at="2026-10-10T00:00:00Z",
        ),
    ]

    req1 = RequirementItem(
        id="REQ-001",
        title="LRU Cache Eviction Policy",
        description="Must support O(1) eviction.",
        category=RequirementCategory.FUNCTIONAL,
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-001", description="Evicts least recently used item.")
        ],
    )

    spec = RequirementSpecification(
        id="spec-test",
        title="Cache Spec",
        source_prompt="LRU cache",
        requirements=[req1],
        assumptions=[],
        created_at="2026-10-10T00:00:00Z",
        updated_at="2026-10-10T00:00:00Z",
    )

    links = svc.generate_candidate_links(spec, artifacts, project_dir=tmp_path)

    assert len(links) >= 2

    # Verify both implementation and test links exist
    impl_links = [l for l in links if l.link_type == LinkType.CANDIDATE_IMPLEMENTATION]
    test_links = [l for l in links if l.link_type == LinkType.CANDIDATE_TEST]

    assert len(impl_links) >= 1
    assert len(test_links) >= 1

    # Verify initial candidate state
    assert impl_links[0].is_confirmed is False

    # Promote to confirmed
    confirmed_link = svc.confirm_link(impl_links[0], is_confirmed=True)
    assert confirmed_link.is_confirmed is True
    assert confirmed_link.link_type == LinkType.CONFIRMED_IMPLEMENTATION
    assert confirmed_link.link_origin == LinkOrigin.DEVELOPER_CONFIRMATION
    assert confirmed_link.confirmed_at is not None
