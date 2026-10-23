"""
FastAPI endpoints for Code Verification & Evidence Engine.
Handles project archive ingestion, requirement-to-code traceability linking,
automated test execution runs, and evidence reporting.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.schemas.verification import (
    ArtifactMetadata,
    ConfirmLinkRequest,
    LinkRequirementsRequest,
    ProjectIngestionReport,
    ProjectSummary,
    TraceabilityLink,
    TriggerRunRequest,
    VerificationRun,
)
from app.services.requirement_intelligence.storage import RequirementRepository
from app.services.verification import (
    CodeArtifactIngestionService,
    CodeTraceabilityService,
    DockerExecutionAdapter,
    IngestionSecurityError,
    VerificationEngine,
    VerificationRepository,
)

router = APIRouter()

ingestion_service = CodeArtifactIngestionService()
traceability_service = CodeTraceabilityService()
verification_engine = VerificationEngine()
repository = VerificationRepository()
req_repository = RequirementRepository()


class DirectFilesUploadPayload(BaseModel):
    """Payload for submitting project files directly via JSON."""
    name: Optional[str] = None
    files: Dict[str, str]


@router.post(
    "/projects",
    response_model=ProjectIngestionReport,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest project code archive",
)
async def ingest_project_archive(
    file: Optional[UploadFile] = File(None),
    project_name: Optional[str] = Form(None),
) -> ProjectIngestionReport:
    """
    Ingests an uploaded ZIP archive containing project source and test code.
    Validates file sizes, rejects path traversal and secrets, and computes SHA-256 fingerprints.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A ZIP archive file must be provided via multipart/form-data upload.",
        )

    try:
        content = await file.read()
        name = project_name or file.filename or "Uploaded-Project"
        if name.endswith(".zip"):
            name = name[:-4]

        report = ingestion_service.ingest_zip_archive(
            archive_bytes=content,
            project_name=name,
        )
        await repository.save_project(report)
        return report

    except IngestionSecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archive rejected: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest archive: {type(exc).__name__}",
        )


@router.post(
    "/projects/json",
    response_model=ProjectIngestionReport,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest project code via JSON dictionary",
)
async def ingest_project_json(payload: DirectFilesUploadPayload) -> ProjectIngestionReport:
    """
    Ingests project files supplied directly as a dictionary of path-to-content.
    """
    if not payload.files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must contain at least one file entry.",
        )

    report = ingestion_service.ingest_files_dictionary(
        files=payload.files,
        project_name=payload.name,
    )
    await repository.save_project(report)
    return report


@router.get(
    "/projects",
    response_model=List[ProjectSummary],
    summary="List ingested projects",
)
async def list_projects() -> List[ProjectSummary]:
    """Lists summaries of all ingested code projects."""
    return await repository.list_projects()


@router.get(
    "/projects/{project_id}",
    response_model=ProjectIngestionReport,
    summary="Get project ingestion report",
)
async def get_project(project_id: str) -> ProjectIngestionReport:
    """Retrieves full report and artifact list for an ingested project."""
    project = await repository.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )
    return project


@router.get(
    "/projects/{project_id}/artifacts",
    response_model=List[ArtifactMetadata],
    summary="List inventoried artifacts",
)
async def list_project_artifacts(project_id: str) -> List[ArtifactMetadata]:
    """Returns all inventoried files and AST symbols for a project."""
    project = await repository.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )
    return project.ingested_artifacts


@router.post(
    "/projects/{project_id}/link-requirements",
    response_model=List[TraceabilityLink],
    summary="Generate candidate requirement traceability links",
)
async def link_requirements(
    project_id: str, payload: LinkRequirementsRequest
) -> List[TraceabilityLink]:
    """
    Generates deterministic candidate links between project artifacts and a Phase 3 specification.
    """
    project = await repository.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    spec = await req_repository.get_specification(payload.specification_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement specification '{payload.specification_id}' not found.",
        )

    proj_dir = ingestion_service.storage_dir / project_id
    links = traceability_service.generate_candidate_links(
        spec=spec,
        artifacts=project.ingested_artifacts,
        project_dir=proj_dir,
    )
    saved_links = await repository.save_links(project_id, links)
    return saved_links


@router.get(
    "/projects/{project_id}/traceability",
    response_model=List[TraceabilityLink],
    summary="Get project traceability links",
)
async def get_project_traceability(project_id: str) -> List[TraceabilityLink]:
    """Returns all candidate and confirmed links for a project."""
    return await repository.get_links(project_id)


@router.post(
    "/projects/{project_id}/confirm-link/{link_id}",
    response_model=TraceabilityLink,
    summary="Confirm or reject a candidate traceability link",
)
async def confirm_link(
    project_id: str, link_id: str, payload: ConfirmLinkRequest
) -> TraceabilityLink:
    """Toggles a link between candidate and confirmed state."""
    updated = await repository.update_link(project_id, link_id, payload.is_confirmed)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Traceability link '{link_id}' not found in project '{project_id}'.",
        )
    return updated


@router.post(
    "/projects/{project_id}/runs",
    response_model=VerificationRun,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger an isolated verification run",
)
async def trigger_verification_run(
    project_id: str, payload: Optional[TriggerRunRequest] = None
) -> VerificationRun:
    """
    Initiates static code inspection and executes tests inside an isolated Docker container.
    Fails closed if the Docker sandbox is unavailable.
    """
    project = await repository.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )

    spec = None
    links = None
    spec_id = payload.specification_id if payload else None
    if spec_id:
        spec = await req_repository.get_specification(spec_id)
        links = await repository.get_links(project_id)

    proj_dir = ingestion_service.storage_dir / project_id
    cmd = payload.test_command if payload else None

    run = verification_engine.execute_verification(
        project_id=project_id,
        project_dir=proj_dir,
        artifacts=project.ingested_artifacts,
        spec=spec,
        links=links,
        test_command=cmd,
    )

    await repository.save_run(run)
    return run


@router.get(
    "/runs/{run_id}",
    response_model=VerificationRun,
    summary="Get verification run details",
)
async def get_verification_run(run_id: str) -> VerificationRun:
    """Retrieves full execution outputs, exit codes, and verdicts for a run."""
    run = await repository.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification run '{run_id}' not found.",
        )
    return run


@router.get(
    "/docker-status",
    summary="Check Docker sandbox availability",
)
async def check_docker_status() -> Dict[str, Any]:
    """Inspects live Docker sandbox daemon availability."""
    adapter = DockerExecutionAdapter()
    ready, msg = adapter.check_docker_availability()
    return {
        "docker_available": ready,
        "message": msg,
        "fail_closed_policy": "Host fallback execution is strictly prohibited.",
    }
