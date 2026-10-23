"""
Isolated Docker Execution Adapter.
Executes automated test suites inside disposable, resource-capped, non-networked Docker containers.
Enforces strict fail-closed security: never executes untrusted uploaded code on the host machine.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class ExecutionResult:
    """Raw execution outcome from the isolation adapter."""

    def __init__(
        self,
        success: bool,
        exit_code: Optional[int],
        stdout: str,
        stderr: str,
        duration_ms: float,
        timed_out: bool = False,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.timed_out = timed_out
        self.error_message = error_message


class DockerExecutionAdapter:
    """
    Adapter responsible for executing test commands inside isolated Docker containers.
    """

    def __init__(self, timeout_seconds: Optional[int] = None):
        self.timeout_seconds = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS

    def check_docker_availability(self) -> Tuple[bool, str]:
        """
        Tests whether the Docker CLI and daemon are operational with a bounded timeout.
        """
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return False, "Docker CLI executable not found on host system PATH."

        try:
            # Probe daemon readiness via 'docker info'
            result = subprocess.run(
                [docker_bin, "info"],
                capture_output=True,
                text=True,
                timeout=2.5,
                check=False,
            )
            if result.returncode == 0:
                return True, "Docker sandbox daemon is active and responsive."
            else:
                return (
                    False,
                    "Docker daemon is stopped or unreachable. Start Docker Desktop/engine.",
                )
        except subprocess.TimeoutExpired:
            return False, "Docker daemon connection probe timed out (2.5s)."
        except Exception as exc:
            return False, f"Docker daemon probe failed: {type(exc).__name__}"

    def run_pytest(
        self,
        project_dir: Path,
        test_command: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """
        Executes pytest in a temporary container with strict resource caps and zero network access.
        Fails closed: if Docker is unavailable, refuses host execution.
        """
        is_ready, reason = self.check_docker_availability()
        if not is_ready:
            return ExecutionResult(
                success=False,
                exit_code=None,
                stdout="",
                stderr="",
                duration_ms=0.0,
                timed_out=False,
                error_message=f"Execution blocked: {reason} (Host fallback prohibited).",
            )

        cmd = test_command or ["pytest", "-v"]
        container_name = f"pf-sandbox-{int(time.time() * 1000)}"

        # Prepare normalized path for volume mount
        abs_proj_path = str(project_dir.resolve()).replace("\\", "/")

        docker_args = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--memory",
            f"{settings.SANDBOX_MAX_MEMORY_MB}m",
            "--cpus",
            "1.0",
            "-v",
            f"{abs_proj_path}:/workspace:ro",
            "-w",
            "/workspace",
            settings.DOCKER_PYTHON_IMAGE,
        ] + cmd

        start_time = time.perf_counter()
        try:
            proc = subprocess.run(
                docker_args,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000

            return ExecutionResult(
                success=(proc.returncode == 0),
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=round(duration_ms, 2),
                timed_out=False,
            )

        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Force kill running container on timeout
            try:
                subprocess.run(["docker", "kill", container_name], capture_output=True, timeout=2.0)
            except Exception:
                pass

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                duration_ms=round(duration_ms, 2),
                timed_out=True,
                error_message=f"Execution timed out after {self.timeout_seconds}s limit.",
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(
                success=False,
                exit_code=None,
                stdout="",
                stderr="",
                duration_ms=round(duration_ms, 2),
                timed_out=False,
                error_message=f"Container execution error: {type(exc).__name__} ({str(exc)[:100]})",
            )
