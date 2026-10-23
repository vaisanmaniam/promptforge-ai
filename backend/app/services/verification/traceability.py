"""
Code and Requirement Traceability Linking Service.
Deterministically maps Phase 3 structured requirements to ingested source code
and test artifacts using AST symbol extraction, explicit ID tagging, and keyword heuristics.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.requirement import RequirementItem, RequirementSpecification
from app.schemas.verification import (
    ArtifactMetadata,
    FileType,
    LinkOrigin,
    LinkType,
    TraceabilityLink,
)


class CodeTraceabilityService:
    """
    Constructs and manages candidate and confirmed links between requirements and source artifacts.
    """

    def generate_candidate_links(
        self,
        spec: RequirementSpecification,
        artifacts: List[ArtifactMetadata],
        project_dir: Path,
    ) -> List[TraceabilityLink]:
        """
        Deterministically produces candidate implementation and test links for each requirement.
        """
        links: List[TraceabilityLink] = []
        link_counter = 1

        # Cache file contents for fast search
        file_contents: Dict[str, str] = {}
        for art in artifacts:
            file_path = project_dir / art.relative_path
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        file_contents[art.relative_path] = f.read()
                except Exception:
                    file_contents[art.relative_path] = ""

        # Map each requirement
        for req in spec.requirements:
            req_id_clean = req.id.upper().strip()
            req_id_pattern = re.compile(rf"\b{re.escape(req_id_clean)}\b", re.IGNORECASE)
            req_id_slug = req_id_clean.lower().replace("-", "_")

            # Extract key semantic stems from requirement title
            title_keywords = self._extract_keywords(req.title)

            matched_links_for_req: Set[Tuple[str, Optional[str]]] = set()

            for art in artifacts:
                content = file_contents.get(art.relative_path, "")
                is_test = art.file_type == FileType.TEST_FILE

                # Strategy 1: Explicit REQ ID tag in code or comments
                if req_id_pattern.search(content) or req_id_slug in content.lower():
                    # Find which specific symbols contain it if possible
                    symbol_matched = None
                    for sym in art.symbols:
                        sym_clean = sym.split(":")[-1]
                        if req_id_slug in sym_clean.lower():
                            symbol_matched = sym_clean
                            break

                    link_key = (art.relative_path, symbol_matched)
                    if link_key not in matched_links_for_req:
                        matched_links_for_req.add(link_key)
                        links.append(
                            TraceabilityLink(
                                id=f"LNK-{link_counter:03d}",
                                project_id=art.project_id,
                                specification_id=spec.id,
                                requirement_id=req.id,
                                artifact_path=art.relative_path,
                                symbol_name=symbol_matched,
                                link_type=(
                                    LinkType.CANDIDATE_TEST
                                    if is_test
                                    else LinkType.CANDIDATE_IMPLEMENTATION
                                ),
                                link_origin=LinkOrigin.STATIC_ANALYSIS,
                                confidence=0.95,
                                is_confirmed=False,
                                rationale=(
                                    f"Explicit requirement identifier '{req.id}' detected in "
                                    f"{'test' if is_test else 'source'} file: {art.relative_path}"
                                ),
                                created_at=datetime.utcnow().isoformat() + "Z",
                            )
                        )
                        link_counter += 1

                # Strategy 2: AST symbol name matches requirement title keywords
                for sym in art.symbols:
                    sym_name = sym.split(":")[-1]
                    sym_tokens = self._extract_keywords(sym_name)
                    common = title_keywords.intersection(sym_tokens)

                    if len(common) >= 1:
                        link_key = (art.relative_path, sym_name)
                        if link_key not in matched_links_for_req:
                            matched_links_for_req.add(link_key)
                            conf = min(0.60 + (0.15 * len(common)), 0.85)
                            links.append(
                                TraceabilityLink(
                                    id=f"LNK-{link_counter:03d}",
                                    project_id=art.project_id,
                                    specification_id=spec.id,
                                    requirement_id=req.id,
                                    artifact_path=art.relative_path,
                                    symbol_name=sym_name,
                                    link_type=(
                                        LinkType.CANDIDATE_TEST
                                        if is_test
                                        else LinkType.CANDIDATE_IMPLEMENTATION
                                    ),
                                    link_origin=LinkOrigin.HEURISTIC_INFERENCE,
                                    confidence=conf,
                                    is_confirmed=False,
                                    rationale=(
                                        f"Symbol '{sym_name}' shares semantic keyword(s) {sorted(list(common))} "
                                        f"with requirement title '{req.title}'."
                                    ),
                                    created_at=datetime.utcnow().isoformat() + "Z",
                                )
                            )
                            link_counter += 1

                # Strategy 3: Relevant filename match when no symbols matched
                if not any(k[0] == art.relative_path for k in matched_links_for_req):
                    fname_tokens = self._extract_keywords(art.relative_path.split("/")[-1])
                    common_fname = title_keywords.intersection(fname_tokens)
                    if len(common_fname) >= 1:
                        link_key = (art.relative_path, None)
                        matched_links_for_req.add(link_key)
                        links.append(
                            TraceabilityLink(
                                id=f"LNK-{link_counter:03d}",
                                project_id=art.project_id,
                                specification_id=spec.id,
                                requirement_id=req.id,
                                artifact_path=art.relative_path,
                                symbol_name=None,
                                link_type=(
                                    LinkType.CANDIDATE_TEST
                                    if is_test
                                    else LinkType.CANDIDATE_IMPLEMENTATION
                                ),
                                link_origin=LinkOrigin.HEURISTIC_INFERENCE,
                                confidence=0.50,
                                is_confirmed=False,
                                rationale=(
                                    f"File name '{art.relative_path}' matches requirement keywords "
                                    f"{sorted(list(common_fname))}."
                                ),
                                created_at=datetime.utcnow().isoformat() + "Z",
                            )
                        )
                        link_counter += 1

        return links

    def confirm_link(
        self, link: TraceabilityLink, is_confirmed: bool = True
    ) -> TraceabilityLink:
        """Promotes or demotes a link between candidate and confirmed."""
        link.is_confirmed = is_confirmed
        if is_confirmed:
            link.confirmed_at = datetime.utcnow().isoformat() + "Z"
            if link.link_type == LinkType.CANDIDATE_IMPLEMENTATION:
                link.link_type = LinkType.CONFIRMED_IMPLEMENTATION
            elif link.link_type == LinkType.CANDIDATE_TEST:
                link.link_type = LinkType.CONFIRMED_TEST
            link.link_origin = LinkOrigin.DEVELOPER_CONFIRMATION
        else:
            link.confirmed_at = None
            if link.link_type == LinkType.CONFIRMED_IMPLEMENTATION:
                link.link_type = LinkType.CANDIDATE_IMPLEMENTATION
            elif link.link_type == LinkType.CONFIRMED_TEST:
                link.link_type = LinkType.CANDIDATE_TEST
        return link

    def _extract_keywords(self, text: str) -> Set[str]:
        """Extracts normalized significant alphanumeric tokens for heuristic matching."""
        # Split on underscores, camelCase transitions, and whitespace
        s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
        words = re.findall(r"[a-zA-Z0-9]+", s1.lower())
        stopwords = {
            "the", "a", "an", "in", "on", "of", "and", "or", "to", "for", "with",
            "is", "are", "be", "must", "should", "test", "implementation", "class", "def",
        }
        return {w for w in words if len(w) > 2 and w not in stopwords}
