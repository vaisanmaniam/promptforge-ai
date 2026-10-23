"""
FastAPI endpoints for Requirement Intelligence and Traceability Engine.
Provides extraction, validation, persistence, NetworkX graph querying,
blast-radius impact analysis, and honest coverage reporting.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.requirement import (
    CoverageReport,
    CreateSpecificationRequest,
    ExtractRequirementsRequest,
    ExtractRequirementsResponse,
    ImpactAnalysisReport,
    RequirementSpecification,
    SpecificationListResponse,
    TraceabilityGraph,
    ValidationReport,
)
from app.schemas.verification import RequirementEvidenceReport
from app.services.requirement_intelligence import (
    CoverageAnalyzer,
    RequirementExtractor,
    RequirementRepository,
    RequirementValidator,
    TraceabilityGraphEngine,
)

router = APIRouter()

extractor = RequirementExtractor()
validator = RequirementValidator()
graph_engine = TraceabilityGraphEngine()
coverage_analyzer = CoverageAnalyzer()
repository = RequirementRepository()


@router.post(
    "/extract",
    response_model=ExtractRequirementsResponse,
    summary="Extract structured requirements and validate",
    status_code=status.HTTP_200_OK,
)
async def extract_requirements(payload: ExtractRequirementsRequest) -> ExtractRequirementsResponse:
    """
    Deterministically transforms natural language prompts into structured requirements,
    acceptance criteria, and explicit vs inferred tags.
    """
    spec = extractor.extract(
        prompt=payload.prompt,
        task_category=payload.task_category,
    )
    val_report = validator.validate(spec)
    cov_report = coverage_analyzer.analyze(spec)

    return ExtractRequirementsResponse(
        specification=spec,
        validation=val_report,
        coverage=cov_report,
    )


@router.post(
    "/specifications",
    response_model=RequirementSpecification,
    summary="Create and persist requirement specification",
    status_code=status.HTTP_201_CREATED,
)
async def create_specification(payload: CreateSpecificationRequest) -> RequirementSpecification:
    """
    Extracts, validates, and persists a requirement specification.
    Persists to PostgreSQL if online, or local storage fallback.
    """
    spec = extractor.extract(
        prompt=payload.prompt,
        task_category=payload.task_category,
        title=payload.title,
    )
    saved_spec = await repository.save_specification(spec)
    return saved_spec


@router.get(
    "/specifications",
    response_model=SpecificationListResponse,
    summary="List requirement specifications",
)
async def list_specifications() -> SpecificationListResponse:
    """
    Lists all saved requirement specifications.
    """
    summaries = await repository.list_specifications()
    return SpecificationListResponse(specifications=summaries, total=len(summaries))


@router.get(
    "/specifications/{spec_id}",
    response_model=RequirementSpecification,
    summary="Retrieve requirement specification by ID",
)
async def get_specification(spec_id: str) -> RequirementSpecification:
    """
    Retrieves full details for a single requirement specification.
    """
    spec = await repository.get_specification(spec_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification with ID '{spec_id}' not found.",
        )
    return spec


@router.get(
    "/specifications/{spec_id}/graph",
    response_model=TraceabilityGraph,
    summary="Retrieve directed traceability graph",
)
async def get_traceability_graph(spec_id: str) -> TraceabilityGraph:
    """
    Constructs and returns the NetworkX directed graph representation
    including prompt root, requirements, dependencies, and cycle analysis.
    """
    spec = await repository.get_specification(spec_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification with ID '{spec_id}' not found.",
        )
    return graph_engine.export_graph(spec)


@router.get(
    "/specifications/{spec_id}/impact/{req_id}",
    response_model=ImpactAnalysisReport,
    summary="Analyze downstream blast-radius for a requirement change",
)
async def analyze_requirement_impact(spec_id: str, req_id: str) -> ImpactAnalysisReport:
    """
    Computes upstream dependencies and downstream blast-radius if a requirement changes.
    """
    spec = await repository.get_specification(spec_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification with ID '{spec_id}' not found.",
        )
    if not any(r.id == req_id for r in spec.requirements):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement '{req_id}' not found in specification '{spec_id}'.",
        )
    return graph_engine.analyze_impact(spec, req_id)


@router.get(
    "/specifications/{spec_id}/coverage",
    response_model=CoverageReport,
    summary="Retrieve honest traceability and acceptance coverage",
)
async def get_coverage_report(spec_id: str) -> CoverageReport:
    """
    Computes truthful traceability and acceptance criteria coverage metrics.
    """
    spec = await repository.get_specification(spec_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification with ID '{spec_id}' not found.",
        )
    return coverage_analyzer.analyze(spec)


@router.get(
    "/specifications/{spec_id}/validation",
    response_model=ValidationReport,
    summary="Retrieve requirement validation findings",
)
async def get_validation_report(spec_id: str) -> ValidationReport:
    """
    Performs validation checks against vague qualifiers, missing criteria, and contradictions.
    """
    spec = await repository.get_specification(spec_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification with ID '{spec_id}' not found.",
        )
    return validator.validate(spec)


@router.get(
    "/specifications/{spec_id}/evidence",
    response_model=RequirementEvidenceReport,
    summary="Retrieve requirement-level verification evidence and coverage",
)
async def get_specification_evidence(
    spec_id: str,
    project_id: Optional[str] = Query(default=None, description="Optional linked project ID"),
) -> RequirementEvidenceReport:
    """
    Computes truthful requirement verification verdicts backed by linked test executions.
    """
    spec = await repository.get_specification(spec_id)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specification with ID '{spec_id}' not found.",
        )

    from app.services.verification.engine import VerificationEngine
    from app.services.verification.storage import VerificationRepository

    v_repo = VerificationRepository()
    v_engine = VerificationEngine()

    links = []
    latest_run = None

    if project_id:
        links = await v_repo.get_links(project_id)
        latest_run = await v_repo.get_latest_run_for_project(project_id)
    else:
        # Check all projects for links to this spec
        projects = await v_repo.list_projects()
        for p in projects:
            p_links = await v_repo.get_links(p.project_id)
            matching = [l for l in p_links if l.specification_id == spec_id]
            if matching:
                links.extend(matching)
                if not latest_run:
                    latest_run = await v_repo.get_latest_run_for_project(p.project_id)
                    project_id = p.project_id

    return v_engine.build_evidence_report(
        spec=spec,
        links=links,
        latest_run=latest_run,
        project_id=project_id,
    )
