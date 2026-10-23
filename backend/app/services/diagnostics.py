import os
import shutil
import time
from typing import Dict, List
import httpx
from app.core.config import get_settings
from app.core.logging import logger
from app.db.session import check_database_health
from app.schemas.system import (
    ComponentDiagnostic,
    ComponentStatus,
    SystemStatusResponse,
)

settings = get_settings()


async def check_database_status() -> ComponentDiagnostic:
    """Evaluate database readiness with connection attempt and sanitization."""
    is_healthy, message, latency = await check_database_health()
    if is_healthy:
        return ComponentDiagnostic(
            status=ComponentStatus.READY,
            message=message,
            latency_ms=latency,
            details={
                "host": settings.POSTGRES_SERVER,
                "port": settings.POSTGRES_PORT,
                "database": settings.POSTGRES_DB,
            },
        )
    return ComponentDiagnostic(
        status=ComponentStatus.UNAVAILABLE,
        message=message,
        latency_ms=latency,
        details={
            "host": settings.POSTGRES_SERVER,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
        },
        troubleshooting=(
            "PostgreSQL is unreachable. If using Docker, run: "
            "'docker compose up -d postgres'. If using a local service, verify the server is running."
        ),
    )


async def check_ai_runtime_status() -> ComponentDiagnostic:
    """
    Evaluate local AI inference runtime (e.g. Ollama).
    Ensures that a reachable server does NOT imply model existence.
    """
    if not settings.AI_RUNTIME_BASE_URL:
        return ComponentDiagnostic(
            status=ComponentStatus.NOT_CONFIGURED,
            message="Local AI runtime endpoint is not configured.",
            troubleshooting="Set AI_RUNTIME_BASE_URL in .env (e.g., http://localhost:11434).",
        )

    start_time = time.perf_counter()
    url = f"{settings.AI_RUNTIME_BASE_URL.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=settings.AI_RUNTIME_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if resp.status_code == 200:
                data = resp.json()
                models_raw = data.get("models", [])
                available_models = [m.get("name", "") for m in models_raw if isinstance(m, dict)]

                # Check if target code model exists in available tags
                target = settings.AI_CODE_MODEL_NAME.lower()
                target_base = target.split(":")[0]
                model_found = any(
                    target == m.lower() or target_base == m.lower().split(":")[0]
                    for m in available_models
                )

                if model_found:
                    return ComponentDiagnostic(
                        status=ComponentStatus.READY,
                        message=f"Local AI runtime reachable. Code model '{settings.AI_CODE_MODEL_NAME}' is ready.",
                        latency_ms=latency_ms,
                        details={
                            "runtime_url": settings.AI_RUNTIME_BASE_URL,
                            "target_model": settings.AI_CODE_MODEL_NAME,
                            "installed_models": available_models,
                        },
                    )
                else:
                    return ComponentDiagnostic(
                        status=ComponentStatus.UNAVAILABLE,
                        message=(
                            f"AI runtime is reachable, but target model "
                            f"'{settings.AI_CODE_MODEL_NAME}' is not downloaded."
                        ),
                        latency_ms=latency_ms,
                        details={
                            "runtime_url": settings.AI_RUNTIME_BASE_URL,
                            "target_model": settings.AI_CODE_MODEL_NAME,
                            "installed_models": available_models,
                        },
                        troubleshooting=(
                            f"Pull the model locally using: 'ollama pull {settings.AI_CODE_MODEL_NAME}'"
                        ),
                    )

            return ComponentDiagnostic(
                status=ComponentStatus.UNAVAILABLE,
                message=f"AI runtime returned unexpected HTTP status {resp.status_code}.",
                latency_ms=latency_ms,
                troubleshooting="Inspect Ollama service logs to determine runtime health.",
            )

    except httpx.ConnectError:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ComponentDiagnostic(
            status=ComponentStatus.UNAVAILABLE,
            message="Local AI runtime connection refused (Ollama offline).",
            latency_ms=latency_ms,
            troubleshooting=(
                f"Ensure Ollama is installed and running. Start via: 'ollama serve' "
                f"or download from https://ollama.com"
            ),
        )
    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ComponentDiagnostic(
            status=ComponentStatus.UNAVAILABLE,
            message=f"AI runtime connection timed out after {settings.AI_RUNTIME_TIMEOUT_SECONDS}s.",
            latency_ms=latency_ms,
            troubleshooting="Verify AI runtime host accessibility and system workload.",
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return ComponentDiagnostic(
            status=ComponentStatus.UNAVAILABLE,
            message=f"AI runtime check failed ({type(exc).__name__}).",
            latency_ms=latency_ms,
            troubleshooting="Check AI_RUNTIME_BASE_URL in .env configuration.",
        )


def resolve_models_directory() -> str:
    """Resolve model artifacts directory across root and backend working directories."""
    raw = settings.AI_MODELS_DIR
    if os.path.isabs(raw) and os.path.exists(raw):
        return raw

    # Candidate 1: relative to current working directory
    cand1 = os.path.abspath(raw)
    if os.path.exists(cand1):
        return cand1

    # Candidate 2: relative to backend directory parent (monorepo root)
    module_dir = os.path.dirname(os.path.abspath(__file__))  # app/services
    backend_root = os.path.abspath(os.path.join(module_dir, "..", ".."))
    repo_root = os.path.abspath(os.path.join(backend_root, ".."))
    cand2 = os.path.abspath(os.path.join(repo_root, raw.lstrip("./")))
    if os.path.exists(cand2):
        return cand2

    cand3 = os.path.abspath(os.path.join(backend_root, raw.lstrip("./")))
    if os.path.exists(cand3):
        return cand3

    return cand1


def check_model_artifacts_status() -> ComponentDiagnostic:
    """Check local model checkpoint storage and distinguish trained vs untrained state."""
    models_dir = resolve_models_directory()
    if not os.path.exists(models_dir):
        return ComponentDiagnostic(
            status=ComponentStatus.NOT_CONFIGURED,
            message=f"Model artifacts directory '{settings.AI_MODELS_DIR}' does not exist.",
            troubleshooting="Create the model artifacts directory or adjust AI_MODELS_DIR in .env.",
        )

    # Inspect for actual trained checkpoint files (bin, safetensors, pkl, onnx, pt)
    checkpoint_extensions = {".bin", ".safetensors", ".pkl", ".onnx", ".pt", ".joblib"}
    found_checkpoints: List[str] = []

    for root, _, files in os.walk(models_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in checkpoint_extensions:
                rel_path = os.path.relpath(os.path.join(root, f), models_dir)
                found_checkpoints.append(rel_path)

    if not found_checkpoints:
        return ComponentDiagnostic(
            status=ComponentStatus.NOT_TRAINED,
            message="No fine-tuned model checkpoints found. Operating in baseline mode.",
            details={
                "models_directory": settings.AI_MODELS_DIR,
                "found_checkpoints": [],
            },
            troubleshooting=(
                "Phase 1 foundation is active. Model training pipelines will populate "
                "artifacts in subsequent phases."
            ),
        )

    return ComponentDiagnostic(
        status=ComponentStatus.READY,
        message=f"Found {len(found_checkpoints)} model checkpoint artifact(s).",
        details={
            "models_directory": settings.AI_MODELS_DIR,
            "found_checkpoints": found_checkpoints,
        },
    )


def check_sandbox_status() -> ComponentDiagnostic:
    """Inspect execution sandbox availability."""
    if not settings.SANDBOX_ENABLED:
        return ComponentDiagnostic(
            status=ComponentStatus.NOT_CONFIGURED,
            message="Execution sandbox is disabled by default for Phase 1.",
            details={
                "sandbox_enabled": False,
                "isolation_runtime": "docker",
            },
            troubleshooting=(
                "Sandbox isolation will be activated in Phase 4. Set SANDBOX_ENABLED=true "
                "in .env when Docker execution testing is required."
            ),
        )

    # Check if docker executable exists
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return ComponentDiagnostic(
            status=ComponentStatus.UNAVAILABLE,
            message="Docker binary not found on host system PATH.",
            troubleshooting="Install Docker Desktop or add docker CLI to the system PATH.",
        )

    return ComponentDiagnostic(
        status=ComponentStatus.READY,
        message="Docker sandbox CLI detected.",
        details={"docker_binary": docker_bin},
    )


async def get_full_system_status() -> SystemStatusResponse:
    """Aggregate all component status reports truthfully."""
    db_diag = await check_database_status()
    ai_diag = await check_ai_runtime_status()
    model_diag = check_model_artifacts_status()
    sandbox_diag = check_sandbox_status()

    components = {
        "database": db_diag,
        "ai_runtime": ai_diag,
        "model_artifacts": model_diag,
        "sandbox": sandbox_diag,
    }

    # Evaluate overall status
    statuses = [c.status for c in components.values()]
    if all(s == ComponentStatus.READY for s in statuses):
        overall = "ready"
    elif any(s == ComponentStatus.UNAVAILABLE for s in statuses):
        overall = "degraded"
    else:
        overall = "setup_required"

    return SystemStatusResponse(
        overall_status=overall,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        components=components,
    )
