"""
Failure Analysis Service.
Parses genuine verification run failures, pytest tracebacks, and static findings,
correlates failures with requirements and AST symbols, generates ranked evidence-backed hypotheses,
and strictly separates environment obstacles from source code defects.
"""

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from app.schemas.repair import (
    DefectClassification,
    FailureAnalysisReport,
    FailureCategory,
    FailureHypothesis,
)
from app.schemas.verification import (
    ArtifactMetadata,
    ExecutionStatus,
    FileType,
    TraceabilityLink,
    VerificationRun,
)


class FailureAnalyzer:
    """
    Diagnoses test failures and static analysis warnings from VerificationRun records.
    """

    def analyze_run_failures(
        self,
        run: VerificationRun,
        artifacts: List[ArtifactMetadata],
        links: List[TraceabilityLink],
        project_dir: Optional[Path] = None,
    ) -> List[FailureAnalysisReport]:
        """
        Parses all failure occurrences within a VerificationRun into structured diagnostic reports.
        """
        now = datetime.now(timezone.utc).isoformat()
        reports: List[FailureAnalysisReport] = []

        # 1. Environment / Infrastructure obstacles (Strictly not classified as code defects)
        if run.status == ExecutionStatus.UNAVAILABLE:
            reports.append(
                FailureAnalysisReport(
                    failure_id=f"FAIL-ENV-{uuid.uuid4().hex[:6].upper()}",
                    run_id=run.id,
                    project_id=run.project_id,
                    test_id="ENVIRONMENT::DOCKER_SANDBOX",
                    category=FailureCategory.ENVIRONMENT_BLOCKED,
                    classification=DefectClassification.ENVIRONMENT_ISSUE,
                    traceback_excerpt=run.stderr or run.stdout or "Docker sandbox is offline or unavailable.",
                    suspected_file=None,
                    suspected_line=None,
                    related_requirement_ids=[],
                    hypotheses=[
                        FailureHypothesis(
                            rank=1,
                            description="Docker daemon is stopped or container execution failed closed without running code.",
                            confidence=1.0,
                            evidence_basis="Sandbox runner reported ExecutionStatus.UNAVAILABLE.",
                        )
                    ],
                    created_at=now,
                )
            )
            return reports

        if run.status == ExecutionStatus.TIMED_OUT:
            reports.append(
                FailureAnalysisReport(
                    failure_id=f"FAIL-TIME-{uuid.uuid4().hex[:6].upper()}",
                    run_id=run.id,
                    project_id=run.project_id,
                    test_id="ENVIRONMENT::TIMEOUT",
                    category=FailureCategory.TIMEOUT,
                    classification=DefectClassification.ENVIRONMENT_ISSUE,
                    traceback_excerpt=run.stderr or "Container execution exceeded hard timeout threshold.",
                    suspected_file=None,
                    suspected_line=None,
                    related_requirement_ids=[],
                    hypotheses=[
                        FailureHypothesis(
                            rank=1,
                            description="Test execution hung or infinite loop exceeded sandbox timeout.",
                            confidence=0.9,
                            evidence_basis="Process terminated by container timer.",
                        )
                    ],
                    created_at=now,
                )
            )
            return reports

        # 2. Static Analysis / Syntax Failures
        if not run.static_analysis_passed and run.static_findings:
            for idx, finding in enumerate(run.static_findings):
                # Try to extract filename and line number
                # e.g. "SyntaxError in 'calculator.py' line 4: invalid syntax"
                suspect_file = None
                suspect_line = None
                m_file = re.search(r"'([^']+)'", finding)
                if m_file:
                    suspect_file = m_file.group(1).replace("\\", "/")
                m_line = re.search(r"line\s+(\d+)", finding, re.IGNORECASE)
                if m_line:
                    suspect_line = int(m_line.group(1))

                is_syntax = "syntaxerror" in finding.lower()
                cat = FailureCategory.SYNTAX_ERROR if is_syntax else FailureCategory.STATIC_ANALYSIS_VIOLATION

                # Correlate requirements
                rel_reqs = self._find_related_requirements(suspect_file, links)

                reports.append(
                    FailureAnalysisReport(
                        failure_id=f"FAIL-STAT-{idx+1:03d}-{uuid.uuid4().hex[:4].upper()}",
                        run_id=run.id,
                        project_id=run.project_id,
                        test_id=f"STATIC::{suspect_file or 'SOURCE'}",
                        category=cat,
                        classification=DefectClassification.CODE_DEFECT,
                        traceback_excerpt=finding,
                        suspected_file=suspect_file,
                        suspected_line=suspect_line,
                        related_requirement_ids=rel_reqs,
                        hypotheses=[
                            FailureHypothesis(
                                rank=1,
                                description=f"Static AST inspection flagged: {finding}",
                                confidence=0.95,
                                evidence_basis=finding,
                                suspected_file=suspect_file,
                                suspected_line=suspect_line,
                            )
                        ],
                        created_at=now,
                    )
                )

        # 3. Pytest Output Failures (Individual Test Blocks)
        parsed_failures = self._parse_pytest_failure_sections(run.stdout)
        for idx, pf in enumerate(parsed_failures):
            test_id = pf["test_id"]
            traceback_text = pf["traceback"]
            category = pf["category"]
            suspect_file = pf.get("suspected_file")
            suspect_line = pf.get("suspected_line")

            # If suspected file is test file, attempt to find target source file via traceability links or convention
            rel_reqs = self._find_related_requirements(suspect_file or test_id, links)
            source_file = self._find_source_file_from_links(rel_reqs, links) or suspect_file

            if source_file and ("test" in source_file.lower() or source_file.startswith("tests/")):
                candidate_name = Path(source_file).name
                if candidate_name.startswith("test_"):
                    base_name = candidate_name[5:]
                    for art in artifacts:
                        if art.file_type == FileType.SOURCE_FILE and (
                            art.relative_path.endswith(base_name)
                            or art.relative_path.replace("\\", "/").endswith(base_name)
                        ):
                            source_file = art.relative_path
                            break

            hypotheses = self._rank_hypotheses(
                category=category,
                traceback=traceback_text,
                suspect_file=source_file,
                suspect_line=suspect_line,
                test_id=test_id,
            )

            reports.append(
                FailureAnalysisReport(
                    failure_id=f"FAIL-TEST-{idx+1:03d}-{uuid.uuid4().hex[:4].upper()}",
                    run_id=run.id,
                    project_id=run.project_id,
                    test_id=test_id,
                    category=category,
                    classification=DefectClassification.CODE_DEFECT,
                    traceback_excerpt=traceback_text[:1500],
                    suspected_file=source_file,
                    suspected_line=suspect_line,
                    related_requirement_ids=rel_reqs,
                    hypotheses=hypotheses,
                    created_at=now,
                )
            )

        return reports

    def _parse_pytest_failure_sections(self, stdout: str) -> List[Dict[str, Any]]:
        """Splits pytest stdout into distinct failure sections and extracts stack traces."""
        failures = []
        if not stdout:
            return failures

        # Section pattern: ______________________________ test_name ______________________________
        sections = re.split(r"_{10,}\s+([\w_]+|test_[\w_]+)\s+_{10,}", stdout)

        if len(sections) > 1:
            for i in range(1, len(sections), 2):
                test_name = sections[i]
                traceback_block = sections[i + 1] if i + 1 < len(sections) else ""

                # Extract failed node id from summary if possible
                node_match = re.search(rf"([\w/\.\-]+::{re.escape(test_name)})", stdout)
                test_id = node_match.group(1) if node_match else f"tests::{test_name}"

                cat, s_file, s_line = self._analyze_traceback_content(traceback_block)
                failures.append(
                    {
                        "test_id": test_id,
                        "traceback": f"_{test_name}_\n{traceback_block.strip()}",
                        "category": cat,
                        "suspected_file": s_file,
                        "suspected_line": s_line,
                    }
                )
        else:
            # Fallback line-by-line FAILED matcher
            for line in stdout.splitlines():
                if "FAILED " in line:
                    m = re.search(r"FAILED\s+([\w/\.\-]+::[\w_]+)(?:\s+-\s+(.*))?", line)
                    if m:
                        t_id = m.group(1)
                        msg = m.group(2) or "Test assertion or execution failure"
                        cat = (
                            FailureCategory.ASSERTION_FAILURE
                            if "assertion" in msg.lower()
                            else FailureCategory.EXCEPTION
                        )
                        failures.append(
                            {
                                "test_id": t_id,
                                "traceback": line,
                                "category": cat,
                                "suspected_file": t_id.split("::")[0],
                                "suspected_line": None,
                            }
                        )

        return failures

    def _analyze_traceback_content(
        self, tb: str
    ) -> Tuple[FailureCategory, Optional[str], Optional[int]]:
        """Parses error type and most relevant source frame."""
        tb_lower = tb.lower()
        if "assertionerror" in tb_lower:
            cat = FailureCategory.ASSERTION_FAILURE
        elif "syntaxerror" in tb_lower:
            cat = FailureCategory.SYNTAX_ERROR
        elif "modulenotfounderror" in tb_lower or "importerror" in tb_lower:
            cat = FailureCategory.IMPORT_ERROR
        elif any(e in tb_lower for e in ["zerodivisionerror", "keyerror", "indexerror", "typeerror", "valueerror"]):
            cat = FailureCategory.EXCEPTION
        else:
            cat = FailureCategory.EXCEPTION

        # Search for file and line number: File "xxx.py", line XX, in yyy OR xxx.py:line: in yyy
        suspect_file = None
        suspect_line = None

        frames = re.findall(r'File\s+"([^"]+)",\s+line\s+(\d+)', tb)
        if not frames:
            frames = re.findall(r'([\w/\.\-]+\.py):(\d+)', tb)

        if frames:
            # Prefer non-test files first
            non_test_frames = [f for f in frames if "test" not in f[0].lower()]
            if non_test_frames:
                suspect_file = non_test_frames[-1][0].replace("\\", "/")
                suspect_line = int(non_test_frames[-1][1])
            else:
                # Use last frame
                suspect_file = frames[-1][0].replace("\\", "/")
                suspect_line = int(frames[-1][1])

        return cat, suspect_file, suspect_line

    def _find_related_requirements(
        self, file_path: Optional[str], links: List[TraceabilityLink]
    ) -> List[str]:
        """Maps file path or test identifier to linked requirement IDs."""
        if not file_path:
            return []
        req_ids = []
        norm = file_path.replace("\\", "/")
        for l in links:
            l_path = l.artifact_path.replace("\\", "/")
            if l_path in norm or norm in l_path:
                req_ids.append(l.requirement_id)
        return sorted(list(set(req_ids)))

    def _find_source_file_from_links(
        self, req_ids: List[str], links: List[TraceabilityLink]
    ) -> Optional[str]:
        """Finds primary implementation file linked to the same requirements."""
        for r_id in req_ids:
            for l in links:
                if l.requirement_id == r_id and "implementation" in l.link_type.value:
                    return l.artifact_path.replace("\\", "/")
        return None

    def _rank_hypotheses(
        self,
        category: FailureCategory,
        traceback: str,
        suspect_file: Optional[str],
        suspect_line: Optional[int],
        test_id: str,
    ) -> List[FailureHypothesis]:
        """Generates ranked, evidence-grounded hypotheses."""
        hypotheses = []

        if category == FailureCategory.ASSERTION_FAILURE:
            # Check for assert diff: e.g. assert -1 == 2
            diff_match = re.search(r"assert\s+([^\n]+)", traceback)
            assert_stmt = diff_match.group(1) if diff_match else "Assertion failed"

            hypotheses.append(
                FailureHypothesis(
                    rank=1,
                    description=f"Implementation returned unexpected value: {assert_stmt.strip()}",
                    confidence=0.88,
                    evidence_basis=f"Pytest assertion failure in {test_id}: '{assert_stmt.strip()}'",
                    suspected_file=suspect_file,
                    suspected_line=suspect_line,
                )
            )
            hypotheses.append(
                FailureHypothesis(
                    rank=2,
                    description="Test expectation may be incorrect or asserting outdated requirement contract.",
                    confidence=0.35,
                    evidence_basis="Secondary hypothesis considering possible test defect.",
                    suspected_file=suspect_file,
                    suspected_line=suspect_line,
                )
            )
        elif category == FailureCategory.IMPORT_ERROR:
            hypotheses.append(
                FailureHypothesis(
                    rank=1,
                    description="Missing module or package import in module namespace.",
                    confidence=0.92,
                    evidence_basis=traceback.splitlines()[-1] if traceback else "ImportError",
                    suspected_file=suspect_file,
                    suspected_line=suspect_line,
                )
            )
        elif category == FailureCategory.SYNTAX_ERROR:
            hypotheses.append(
                FailureHypothesis(
                    rank=1,
                    description="Invalid Python syntax preventing module compilation.",
                    confidence=0.98,
                    evidence_basis="SyntaxError exception during import/parse.",
                    suspected_file=suspect_file,
                    suspected_line=suspect_line,
                )
            )
        else:
            hypotheses.append(
                FailureHypothesis(
                    rank=1,
                    description="Unhandled exception during test execution.",
                    confidence=0.75,
                    evidence_basis=traceback.splitlines()[-1] if traceback else "Runtime Exception",
                    suspected_file=suspect_file,
                    suspected_line=suspect_line,
                )
            )

        return hypotheses
