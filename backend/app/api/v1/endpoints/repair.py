"""
Failure-Guided Automated Code Repair REST API Endpoints.
Provides endpoints for failure diagnosis, candidate repair proposal generation,
explicit approval/rejection lifecycle, patch application, verification comparison,
and immutable audit history.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import get_settings
from app.schemas.repair import (
    FailureAnalysisReport,
    GenerateProposalRequest,
    PatchApplicationResult,
    ProposalDecisionRequest,
    RepairAuditLogEntry,
    RepairCandidateStatus,
    RepairProposal,
    RepairVerificationComparison,
)
from app.services.diagnostics import check_ai_runtime_status, check_sandbox_status
from app.services.repair.failure_analyzer import FailureAnalyzer
from app.services.repair.generator import RepairCandidateGenerator
from app.services.repair.lifecycle import RepairLifecycleCoordinator
from app.services.repair.patcher import SecurePatcher
from app.services.repair.storage import RepairRepository
from app.services.verification.engine import VerificationEngine
from app.services.verification.storage import VerificationRepository

router = APIRouter()
settings = get_settings()

# Initialize services and repositories
verification_repo = VerificationRepository()
repair_repo = RepairRepository()
patcher = SecurePatcher()
verification_engine = VerificationEngine()
analyzer = FailureAnalyzer()
generator = RepairCandidateGenerator()
lifecycle = RepairLifecycleCoordinator(
    repair_repo=repair_repo,
    verification_repo=verification_repo,
    patcher=patcher,
    verification_engine=verification_engine,
)


@router.post(
    "/analyze/{run_id}",
    response_model=List[FailureAnalysisReport],
    status_code=status.HTTP_200_OK,
    summary="Analyze verification failures for a run",
)
async def analyze_run_failures(run_id: str) -> List[FailureAnalysisReport]:
    """
    Parses test assertion diffs, exception tracebacks, and static analysis violations
    from a VerificationRun record into structured, ranked failure reports.
    """
    run = await verification_repo.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification run '{run_id}' not found.",
        )

    project = await verification_repo.get_project(run.project_id)
    artifacts = project.ingested_artifacts if project else []
    links = await verification_repo.get_links(run.project_id)

    reports = analyzer.analyze_run_failures(
        run=run,
        artifacts=artifacts,
        links=links,
    )

    for r in reports:
        repair_repo.save_failure(r)

    return reports


@router.get(
    "/failures/{failure_id}",
    response_model=FailureAnalysisReport,
    status_code=status.HTTP_200_OK,
    summary="Get detailed failure diagnosis report",
)
async def get_failure_report(failure_id: str) -> FailureAnalysisReport:
    """Retrieves an existing failure analysis diagnosis by ID."""
    report = repair_repo.get_failure(failure_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure analysis report '{failure_id}' not found.",
        )
    return report


@router.post(
    "/proposals",
    response_model=RepairProposal,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a targeted repair candidate proposal",
)
async def generate_proposal(request: GenerateProposalRequest) -> RepairProposal:
    """
    Generates a reviewable repair candidate with unified diff, risk rating,
    and explanation using deterministic rules or local code model.
    """
    failure = repair_repo.get_failure(request.failure_id)
    if not failure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failure '{request.failure_id}' not found. Run failure analysis first.",
        )

    if failure.category in ("environment_blocked", "timeout"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate code repair proposal for infrastructure or environment obstacles. Verify Docker sandbox status first.",
        )

    project = await verification_repo.get_project(failure.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{failure.project_id}' not found.",
        )

    proposal = generator.generate_repair_proposal(
        failure=failure,
        project=project,
        generator_override=request.generator_override,
    )

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No viable repair candidate could be generated for this failure.",
        )

    repair_repo.save_proposal(proposal)

    # Record initial audit entry
    repair_repo.record_audit_event(
        repair_id=proposal.repair_id,
        action="PROPOSE",
        actor="developer",
        from_status="none",
        to_status=proposal.status.value,
        details={
            "generator_type": proposal.generator_type,
            "risk_level": proposal.risk_level.value,
            "target": proposal.target_artifact_path,
        },
    )

    return proposal


@router.get(
    "/proposals",
    response_model=List[RepairProposal],
    status_code=status.HTTP_200_OK,
    summary="List code repair proposals",
)
async def list_proposals(
    project_id: Optional[str] = Query(None, description="Filter proposals by project ID")
) -> List[RepairProposal]:
    """Lists all generated repair proposals, optionally filtered by project ID."""
    return repair_repo.list_proposals(project_id=project_id)


@router.get(
    "/proposals/{repair_id}",
    response_model=RepairProposal,
    status_code=status.HTTP_200_OK,
    summary="Get repair proposal by ID",
)
async def get_proposal(repair_id: str) -> RepairProposal:
    """Retrieves a specific repair proposal by repair ID."""
    proposal = repair_repo.get_proposal(repair_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{repair_id}' not found.",
        )
    return proposal


@router.post(
    "/proposals/{repair_id}/approve",
    response_model=RepairProposal,
    status_code=status.HTTP_200_OK,
    summary="Explicitly approve a repair proposal",
)
async def approve_proposal(
    repair_id: str,
    request: Optional[ProposalDecisionRequest] = None,
) -> RepairProposal:
    """Transitions a repair proposal from PROPOSED to APPROVED."""
    reason = request.decision_reason if request else None
    success, proposal, msg = await lifecycle.approve_proposal(
        repair_id=repair_id,
        reason=reason,
    )

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{repair_id}' not found.",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return proposal


@router.post(
    "/proposals/{repair_id}/reject",
    response_model=RepairProposal,
    status_code=status.HTTP_200_OK,
    summary="Reject a repair proposal",
)
async def reject_proposal(
    repair_id: str,
    request: Optional[ProposalDecisionRequest] = None,
) -> RepairProposal:
    """Rejects a proposed repair with optional reason."""
    reason = request.decision_reason if request else None
    success, proposal, msg = await lifecycle.reject_proposal(
        repair_id=repair_id,
        reason=reason,
    )

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{repair_id}' not found.",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return proposal


@router.post(
    "/proposals/{repair_id}/apply",
    response_model=PatchApplicationResult,
    status_code=status.HTTP_200_OK,
    summary="Safely apply approved patch to workspace",
)
async def apply_proposal(repair_id: str) -> PatchApplicationResult:
    """
    Applies an approved patch to the project workspace with strict jail checking,
    hash validation against drift, and pre-patch snapshot creation.
    """
    success, proposal, result = await lifecycle.apply_proposal(repair_id=repair_id)

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{repair_id}' not found.",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    return result


@router.post(
    "/proposals/{repair_id}/verify",
    response_model=RepairVerificationComparison,
    status_code=status.HTTP_200_OK,
    summary="Execute post-repair verification in isolated Docker sandbox",
)
async def verify_proposal(repair_id: str) -> RepairVerificationComparison:
    """
    Executes post-repair test suite in Docker container to truthfully verify
    if the repair fixed targeted tests without introducing regressions.
    """
    success, proposal, comp, msg = await lifecycle.verify_proposal(repair_id=repair_id)

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{repair_id}' not found.",
        )

    if not comp:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE if "Docker" in msg else status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return comp


@router.post(
    "/proposals/{repair_id}/rollback",
    status_code=status.HTTP_200_OK,
    summary="Roll back an applied patch to pre-patch snapshot",
)
async def rollback_proposal(repair_id: str) -> Dict[str, Any]:
    """Restores the target artifact to its immutable pre-patch snapshot."""
    success, proposal, msg = await lifecycle.rollback_proposal(repair_id=repair_id)

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{repair_id}' not found.",
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    return {
        "success": True,
        "repair_id": repair_id,
        "status": proposal.status.value,
        "message": msg,
    }


@router.get(
    "/history",
    response_model=List[RepairAuditLogEntry],
    status_code=status.HTTP_200_OK,
    summary="Get immutable repair audit ledger",
)
async def get_repair_history(
    repair_id: Optional[str] = Query(None, description="Filter audit trail by repair ID")
) -> List[RepairAuditLogEntry]:
    """Retrieves immutable audit trail of all repair lifecycle actions."""
    return repair_repo.get_audit_trail(repair_id=repair_id)


@router.get(
    "/runtime/status",
    status_code=status.HTTP_200_OK,
    summary="Repair engine runtime diagnostic status",
)
async def get_repair_runtime_status() -> Dict[str, Any]:
    """
    Truthfully reports the status of deterministic repair engine,
    local code model (Ollama), and Docker sandbox availability.
    """
    ai_diag = await check_ai_runtime_status()
    sandbox_diag = check_sandbox_status()

    return {
        "deterministic_engine": True,
        "local_code_model": ai_diag.status.value,
        "code_model_name": settings.AI_CODE_MODEL_NAME,
        "docker_sandbox": sandbox_diag.status.value,
        "details": {
            "ai_runtime": ai_diag.model_dump(),
            "sandbox": sandbox_diag.model_dump(),
        },
    }
