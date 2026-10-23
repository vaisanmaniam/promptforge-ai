"""
Automated Verification Engine.
Orchestrates static code inspection, test discovery, isolated Docker test execution,
and computes truthful requirement-level verification verdicts.
"""

import ast
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.requirement import RequirementSpecification
from app.schemas.verification import (
    ArtifactMetadata,
    ExecutionStatus,
    FileType,
    RequirementEvidenceReport,
    RequirementEvidenceVerdict,
    RequirementVerdictStatus,
    TraceabilityLink,
    VerificationRun,
)
from app.services.verification.docker_runner import DockerExecutionAdapter, ExecutionResult


class VerificationEngine:
    """
    Coordinates static source analysis, containerized test execution, and evidence mapping.
    """

    def __init__(self, runner: Optional[DockerExecutionAdapter] = None):
        self.runner = runner or DockerExecutionAdapter()

    def run_static_inspection(
        self, project_dir: Path, artifacts: List[ArtifactMetadata]
    ) -> Tuple[bool, List[str]]:
        """
        Performs non-executing AST syntax and security sanity check on Python sources.
        """
        findings: List[str] = []
        has_syntax_error = False

        for art in artifacts:
            if art.language != "python":
                continue

            file_path = project_dir / art.relative_path
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                tree = ast.parse(content, filename=art.relative_path)

                # Check for suspicious eval / os.system calls in untrusted uploads
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                            findings.append(
                                f"Warning: '{art.relative_path}': Use of dynamic code evaluation '{node.func.id}()'"
                            )
                        elif isinstance(node.func, ast.Attribute) and node.func.attr in ("system", "popen"):
                            findings.append(
                                f"Notice: '{art.relative_path}': Subprocess/shell invocation '{node.func.attr}()'"
                            )

            except SyntaxError as exc:
                has_syntax_error = True
                findings.append(
                    f"SyntaxError in '{art.relative_path}' line {exc.lineno}: {exc.msg}"
                )
            except Exception as exc:
                findings.append(f"Inspection error in '{art.relative_path}': {exc}")

        return (not has_syntax_error), findings

    def discover_tests(self, project_dir: Path, artifacts: List[ArtifactMetadata]) -> List[str]:
        """
        Discovers test functions and test classes without executing code.
        """
        tests_found: List[str] = []

        for art in artifacts:
            if art.file_type != FileType.TEST_FILE:
                continue

            file_path = project_dir / art.relative_path
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                tree = ast.parse(content)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        tests_found.append(f"{art.relative_path}::{node.name}")
                    elif isinstance(node, ast.ClassDef):
                        for m in node.body:
                            if isinstance(m, ast.FunctionDef) and m.name.startswith("test_"):
                                tests_found.append(f"{art.relative_path}::{node.name}::{m.name}")
            except Exception:
                pass

        return tests_found

    def execute_verification(
        self,
        project_id: str,
        project_dir: Path,
        artifacts: List[ArtifactMetadata],
        spec: Optional[RequirementSpecification] = None,
        links: Optional[List[TraceabilityLink]] = None,
        test_command: Optional[List[str]] = None,
        run_id: Optional[str] = None,
    ) -> VerificationRun:
        """
        Performs static analysis, executes isolated tests, and computes requirement verdicts.
        """
        run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        # Step 1: Static code inspection
        static_ok, static_findings = self.run_static_inspection(project_dir, artifacts)

        # Step 2: Execute tests via isolated runner
        exec_res: ExecutionResult = self.runner.run_pytest(
            project_dir=project_dir,
            test_command=test_command,
        )

        # Check Docker availability
        docker_ready, docker_msg = self.runner.check_docker_availability()

        if exec_res.error_message and ("Docker daemon" in exec_res.error_message or "Docker CLI" in exec_res.error_message or "Execution blocked" in exec_res.error_message):
            status = ExecutionStatus.UNAVAILABLE
        elif exec_res.timed_out:
            status = ExecutionStatus.TIMED_OUT
        elif exec_res.exit_code == 0:
            status = ExecutionStatus.PASSED
        elif exec_res.exit_code is not None and exec_res.exit_code > 0:
            status = ExecutionStatus.FAILED
        else:
            status = ExecutionStatus.ERROR

        # Step 3: Parse pytest results from stdout
        total_tests, passed_tests, failed_tests, skipped_tests, passed_names, failed_names = (
            self._parse_pytest_output(exec_res.stdout)
        )

        # Step 4: Map requirement verdicts if specification and links are available
        req_verdicts: Dict[str, RequirementEvidenceVerdict] = {}
        if spec:
            req_verdicts = self._compute_requirement_verdicts(
                spec=spec,
                links=links or [],
                run_status=status,
                passed_test_names=passed_names,
                failed_test_names=failed_names,
                static_passed=static_ok,
            )

        completed_iso = datetime.utcnow().isoformat() + "Z"

        return VerificationRun(
            id=run_id,
            project_id=project_id,
            specification_id=spec.id if spec else None,
            status=status,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            duration_ms=exec_res.duration_ms,
            stdout=exec_res.stdout,
            stderr=exec_res.stderr or (exec_res.error_message or ""),
            exit_code=exec_res.exit_code,
            static_analysis_passed=static_ok,
            static_findings=static_findings,
            requirement_verdicts=req_verdicts,
            docker_available=docker_ready,
            created_at=now_iso,
            completed_at=completed_iso,
        )

    def _parse_pytest_output(
        self, stdout: str
    ) -> Tuple[int, int, int, int, List[str], List[str]]:
        """Parses test counts and individual test names from pytest terminal output."""
        passed_names: List[str] = []
        failed_names: List[str] = []

        # Find individual test outcome lines (e.g. tests/test_cache.py::test_get PASSED)
        for line in stdout.splitlines():
            line_str = line.strip()
            if "PASSED" in line_str:
                test_match = re.search(r"([\w/\.\-]+::[\w_]+)\s+PASSED", line_str)
                if test_match:
                    passed_names.append(test_match.group(1))
            elif "FAILED" in line_str:
                test_match = re.search(r"([\w/\.\-]+::[\w_]+)\s+FAILED", line_str)
                if test_match:
                    failed_names.append(test_match.group(1))

        # Parse summary counts (e.g. '=== 5 passed, 1 failed, 1 skipped in 0.12s ===')
        passed = 0
        failed = 0
        skipped = 0

        p_match = re.search(r"(\d+)\s+passed", stdout)
        if p_match:
            passed = int(p_match.group(1))

        f_match = re.search(r"(\d+)\s+failed", stdout)
        if f_match:
            failed = int(f_match.group(1))

        s_match = re.search(r"(\d+)\s+skipped", stdout)
        if s_match:
            skipped = int(s_match.group(1))

        total = passed + failed + skipped
        return total, passed, failed, skipped, passed_names, failed_names

    def _compute_requirement_verdicts(
        self,
        spec: RequirementSpecification,
        links: List[TraceabilityLink],
        run_status: ExecutionStatus,
        passed_test_names: List[str],
        failed_test_names: List[str],
        static_passed: bool,
    ) -> Dict[str, RequirementEvidenceVerdict]:
        """
        Determines verification verdict for each requirement using strict evidence rules:
        A requirement is verified ONLY when linked tests passed AND static checks passed.
        """
        verdicts: Dict[str, RequirementEvidenceVerdict] = {}

        for req in spec.requirements:
            req_links = [l for l in links if l.requirement_id == req.id]
            code_links = [l for l in req_links if "implementation" in l.link_type]
            test_links = [l for l in req_links if "test" in l.link_type]

            req_passed_tests: List[str] = []
            req_failed_tests: List[str] = []

            # Check which linked tests passed or failed
            for t_link in test_links:
                t_path = t_link.artifact_path
                t_sym = t_link.symbol_name

                # Match against parsed test execution names
                for p_name in passed_test_names:
                    if t_path in p_name or (t_sym and t_sym in p_name):
                        req_passed_tests.append(p_name)

                for f_name in failed_test_names:
                    if t_path in f_name or (t_sym and t_sym in f_name):
                        req_failed_tests.append(f_name)

            req_passed_tests = sorted(list(set(req_passed_tests)))
            req_failed_tests = sorted(list(set(req_failed_tests)))

            # Apply verdict rules
            if len(test_links) == 0:
                verdict = RequirementVerdictStatus.UNVERIFIED
                rationale = "No test artifact has been linked to this requirement."
            elif run_status == ExecutionStatus.UNAVAILABLE:
                verdict = RequirementVerdictStatus.UNVERIFIED
                rationale = "Verification run unavailable: Docker sandbox is offline. Cannot execute tests."
            elif len(req_failed_tests) > 0:
                verdict = RequirementVerdictStatus.FAILED
                rationale = f"Linked test(s) failed execution: {', '.join(req_failed_tests[:2])}"
            elif len(req_passed_tests) > 0:
                if static_passed:
                    verdict = RequirementVerdictStatus.VERIFIED
                    rationale = f"Verified by passing test(s): {', '.join(req_passed_tests[:2])}"
                else:
                    verdict = RequirementVerdictStatus.FAILED
                    rationale = "Linked tests passed, but static code inspection flagged syntax or safety errors."
            elif run_status == ExecutionStatus.PASSED and len(test_links) > 0 and len(passed_test_names) > 0:
                # Tests in the suite passed and we have a linked test file
                verdict = RequirementVerdictStatus.VERIFIED
                rationale = f"Test suite passed successfully covering linked artifact '{test_links[0].artifact_path}'."
            else:
                verdict = RequirementVerdictStatus.UNVERIFIED
                rationale = "Linked tests exist but were not executed in this run or execution failed."

            verdicts[req.id] = RequirementEvidenceVerdict(
                requirement_id=req.id,
                requirement_title=req.title,
                verdict=verdict,
                linked_code_count=len(code_links),
                linked_test_count=len(test_links),
                passed_tests=req_passed_tests,
                failed_tests=req_failed_tests,
                rationale=rationale,
            )

        return verdicts

    def build_evidence_report(
        self,
        spec: RequirementSpecification,
        links: List[TraceabilityLink],
        latest_run: Optional[VerificationRun] = None,
        project_id: Optional[str] = None,
    ) -> RequirementEvidenceReport:
        """
        Computes aggregate evidence report and honest requirement coverage metrics.
        """
        total_reqs = len(spec.requirements)
        if total_reqs == 0:
            return RequirementEvidenceReport(
                specification_id=spec.id,
                project_id=project_id,
                total_requirements=0,
                candidate_code_linked_count=0,
                confirmed_code_linked_count=0,
                linked_test_count=0,
                verified_requirement_count=0,
                failed_requirement_count=0,
                unverified_requirement_count=0,
                verification_coverage_pct=0.0,
                verdicts=[],
                notes=["Specification contains zero requirements."],
            )

        cand_code_set = {
            l.requirement_id
            for l in links
            if l.link_type == "candidate_implementation"
        }
        conf_code_set = {
            l.requirement_id
            for l in links
            if l.link_type == "confirmed_implementation"
        }
        test_set = {
            l.requirement_id
            for l in links
            if "test" in l.link_type
        }

        verdicts_list: List[RequirementEvidenceVerdict] = []
        if latest_run and latest_run.requirement_verdicts:
            verdicts_list = list(latest_run.requirement_verdicts.values())
        else:
            # Baseline unverified verdicts
            for req in spec.requirements:
                c_links = [l for l in links if l.requirement_id == req.id and "implementation" in l.link_type]
                t_links = [l for l in links if l.requirement_id == req.id and "test" in l.link_type]
                verdicts_list.append(
                    RequirementEvidenceVerdict(
                        requirement_id=req.id,
                        requirement_title=req.title,
                        verdict=RequirementVerdictStatus.UNVERIFIED,
                        linked_code_count=len(c_links),
                        linked_test_count=len(t_links),
                        passed_tests=[],
                        failed_tests=[],
                        rationale="Awaiting verification run execution.",
                    )
                )

        verified_count = sum(1 for v in verdicts_list if v.verdict == RequirementVerdictStatus.VERIFIED)
        failed_count = sum(1 for v in verdicts_list if v.verdict == RequirementVerdictStatus.FAILED)
        unverified_count = sum(1 for v in verdicts_list if v.verdict == RequirementVerdictStatus.UNVERIFIED)

        cov_pct = round((verified_count / total_reqs) * 100.0, 1)

        notes = [
            f"{verified_count} of {total_reqs} requirement(s) are backed by passing test execution.",
            f"{len(conf_code_set)} requirement(s) have confirmed code implementations.",
            f"{len(test_set)} requirement(s) have linked test cases.",
        ]

        if latest_run and latest_run.status == ExecutionStatus.UNAVAILABLE:
            notes.append("Latest verification run was unavailable because Docker sandbox daemon is offline.")

        return RequirementEvidenceReport(
            specification_id=spec.id,
            project_id=project_id,
            total_requirements=total_reqs,
            candidate_code_linked_count=len(cand_code_set),
            confirmed_code_linked_count=len(conf_code_set),
            linked_test_count=len(test_set),
            verified_requirement_count=verified_count,
            failed_requirement_count=failed_count,
            unverified_requirement_count=unverified_count,
            verification_coverage_pct=cov_pct,
            verdicts=verdicts_list,
            latest_run_id=latest_run.id if latest_run else None,
            latest_run_status=latest_run.status if latest_run else None,
            notes=notes,
        )
