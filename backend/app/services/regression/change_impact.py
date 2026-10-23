"""
Change Impact Analysis Service.
Analyzes code modifications against cataloged AST artifacts, links changes
to Phase 3 requirement dependency graphs, propagates downstream blast radius,
and identifies candidate affected tests without fabricating missing metadata.
"""

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import uuid

from app.schemas.regression import (
    AffectedRequirementInfo,
    ChangedFileInfo,
    ChangeImpactReport,
    ChangeType,
)
from app.schemas.requirement import RequirementSpecification
from app.schemas.verification import ArtifactMetadata, FileType, ProjectIngestionReport, TraceabilityLink
from app.services.requirement_intelligence.graph import TraceabilityGraphEngine


class ChangeImpactService:
    """
    Performs structural AST and requirement-graph change impact analysis.
    """

    def __init__(self):
        self.graph_engine = TraceabilityGraphEngine()

    def analyze_change(
        self,
        project: ProjectIngestionReport,
        changed_files: List[str],
        links: List[TraceabilityLink],
        spec: Optional[RequirementSpecification] = None,
        file_contents: Optional[Dict[str, str]] = None,
        diff_text: Optional[str] = None,
        project_dir: Optional[Path] = None,
    ) -> ChangeImpactReport:
        """
        Computes detailed impact scope, changed AST symbols, affected requirements,
        downstream blast radius, and candidate affected test suite.
        """
        analysis_id = f"ANL-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        disclosures: List[str] = []

        if not diff_text:
            disclosures.append("Git unified diff metadata not provided; analyzing explicit changed file list.")

        # Map artifacts by relative path
        artifact_map: Dict[str, ArtifactMetadata] = {
            a.relative_path.replace("\\", "/"): a for a in project.ingested_artifacts
        }

        # 1. Categorize changed files
        changed_file_infos: List[ChangedFileInfo] = []
        changed_symbols_all: Set[str] = set()

        for c_path in changed_files:
            norm_path = c_path.replace("\\", "/")
            existing_art = artifact_map.get(norm_path)

            if existing_art is None:
                # File was added or not previously in catalog
                change_type = ChangeType.ADDED
                is_test = "test" in norm_path.lower()
                symbols = self._extract_symbols_from_content(
                    (file_contents or {}).get(norm_path, "")
                )
            else:
                change_type = ChangeType.MODIFIED
                is_test = existing_art.file_type == FileType.TEST_FILE
                symbols = existing_art.symbols

                # If updated content provided, re-parse symbols
                if file_contents and norm_path in file_contents:
                    new_symbols = self._extract_symbols_from_content(file_contents[norm_path])
                    if new_symbols:
                        symbols = new_symbols

            changed_symbols_all.update(symbols)
            changed_file_infos.append(
                ChangedFileInfo(
                    file_path=norm_path,
                    change_type=change_type,
                    changed_symbols=symbols,
                    is_test=is_test,
                )
            )

        # 2. Map changed code to requirements via Phase 4 traceability links
        directly_affected_req_ids: Set[str] = set()
        req_to_artifacts: Dict[str, List[str]] = {}

        for link in links:
            link_path = link.artifact_path.replace("\\", "/")
            if link_path in [c.file_path for c in changed_file_infos]:
                if "implementation" in link.link_type.value:
                    directly_affected_req_ids.add(link.requirement_id)
                    req_to_artifacts.setdefault(link.requirement_id, []).append(link_path)

        if not links:
            disclosures.append("No Phase 4 traceability links found for project; requirement impact inferred from heuristics.")

        # 3. Propagate impact through Phase 3 Requirement DAG if specification exists
        directly_affected_reqs: List[AffectedRequirementInfo] = []
        downstream_affected_reqs: List[AffectedRequirementInfo] = []
        max_depth = 0

        if spec and directly_affected_req_ids:
            for req_id in sorted(list(directly_affected_req_ids)):
                target_req = next((r for r in spec.requirements if r.id == req_id), None)
                if target_req:
                    directly_affected_reqs.append(
                        AffectedRequirementInfo(
                            requirement_id=target_req.id,
                            title=target_req.title,
                            priority=target_req.priority.value,
                            is_directly_changed=True,
                            impact_distance=0,
                            linked_code_artifacts=req_to_artifacts.get(target_req.id, []),
                        )
                    )

                    # Propagate downstream blast radius using Phase 3 NetworkX engine
                    impact_report = self.graph_engine.analyze_impact(spec, target_req.id)
                    max_depth = max(max_depth, impact_report.impact_depth)

                    for down_id in impact_report.downstream_dependents:
                        down_req = next((r for r in spec.requirements if r.id == down_id), None)
                        if down_req and not any(d.requirement_id == down_id for d in downstream_affected_reqs):
                            downstream_affected_reqs.append(
                                AffectedRequirementInfo(
                                    requirement_id=down_req.id,
                                    title=down_req.title,
                                    priority=down_req.priority.value,
                                    is_directly_changed=False,
                                    impact_distance=1,
                                    linked_code_artifacts=[],
                                )
                            )
        elif not spec:
            disclosures.append("Requirement specification not loaded; downstream blast radius graph traversal skipped.")

        # 4. Count candidate affected tests
        # A test is affected if:
        # - It is directly in changed_files
        # - It verifies an affected (direct or downstream) requirement
        # - It contains or references any changed symbols
        all_affected_req_ids = directly_affected_req_ids.union(
            {d.requirement_id for d in downstream_affected_reqs}
        )

        affected_test_count = 0
        for art in project.ingested_artifacts:
            if art.file_type != FileType.TEST_FILE:
                continue
            art_norm = art.relative_path.replace("\\", "/")

            is_direct_test_mod = art_norm in [c.file_path for c in changed_file_infos]
            is_linked_to_req = any(
                l.artifact_path.replace("\\", "/") == art_norm
                and l.requirement_id in all_affected_req_ids
                and "test" in l.link_type.value
                for l in links
            )
            has_symbol_overlap = any(s in changed_symbols_all for s in art.symbols)

            if is_direct_test_mod or is_linked_to_req or has_symbol_overlap:
                affected_test_count += 1

        return ChangeImpactReport(
            analysis_id=analysis_id,
            project_id=project.project_id,
            changed_files=changed_file_infos,
            changed_symbols=sorted(list(changed_symbols_all)),
            directly_affected_requirements=directly_affected_reqs,
            downstream_affected_requirements=downstream_affected_reqs,
            max_blast_radius_depth=max_depth,
            affected_tests_candidate_count=affected_test_count,
            evidence_disclosures=disclosures,
            created_at=now,
        )

    def _extract_symbols_from_content(self, content: str) -> List[str]:
        """Extracts top-level function and class names using AST."""
        if not content.strip():
            return []
        symbols: List[str] = []
        try:
            tree = ast.parse(content)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append(node.name)
        except Exception:
            pass
        return symbols
