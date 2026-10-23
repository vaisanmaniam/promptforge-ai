"""
Predictive Regression Testing REST API Endpoints.
Provides endpoints for change impact analysis, deterministic & ML test prioritization,
budget-based test selection, historical observations, model lifecycle, and metrics.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ai.regression_model.evaluator import ModelEvaluationPipeline
from ai.regression_model.model import PredictiveRegressionModel
from ai.regression_model.trainer import ModelTrainingPipeline
from app.schemas.regression import (
    ChangeImpactReport,
    ChangeImpactRequest,
    HistoricalObservationSummary,
    ModelEvaluationRequest,
    ModelStatusReport,
    ModelTrainingReport,
    ModelTrainingRequest,
    PrioritizationReport,
    PrioritizationRequest,
    TestSelectionReport,
    TestSelectionRequest,
)
from app.services.regression.analysis_storage import AnalysisRepository
from app.services.regression.change_impact import ChangeImpactService
from app.services.regression.history import TestHistoryRepository
from app.services.regression.selector import TestSelector
from app.services.requirement_intelligence.storage import RequirementRepository
from app.services.verification.engine import VerificationEngine
from app.services.verification.storage import VerificationRepository

router = APIRouter()

# Service instances
verification_repo = VerificationRepository()
requirement_repo = RequirementRepository()
history_repo = TestHistoryRepository()
analysis_repo = AnalysisRepository()
impact_service = ChangeImpactService()
test_selector = TestSelector(history_repo=history_repo)
training_pipeline = ModelTrainingPipeline()
eval_pipeline = ModelEvaluationPipeline()


@router.post(
    "/analyze",
    response_model=ChangeImpactReport,
    status_code=status.HTTP_200_OK,
    summary="Analyze code change impact and affected requirements",
)
async def analyze_change_impact(request: ChangeImpactRequest) -> ChangeImpactReport:
    """
    Analyzes code modifications against project artifacts, extracts changed symbols,
    links changes to requirements, and traverses downstream blast radius.
    """
    project = await verification_repo.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{request.project_id}' not found.",
        )

    links = await verification_repo.get_links(request.project_id)

    # Attempt to locate associated requirement specification
    spec = None
    if links and links[0].specification_id:
        spec = await requirement_repo.get_specification(links[0].specification_id)

    report = impact_service.analyze_change(
        project=project,
        changed_files=request.changed_files,
        links=links,
        spec=spec,
        file_contents=request.file_contents,
        diff_text=request.diff_text,
    )
    analysis_repo.save_analysis(report)
    return report


@router.post(
    "/prioritize",
    response_model=PrioritizationReport,
    status_code=status.HTTP_200_OK,
    summary="Rank tests using selected prioritization strategy",
)
async def prioritize_tests(request: PrioritizationRequest) -> PrioritizationReport:
    """
    Ranks tests by their likelihood of regression detection for a change.
    Discloses transparent fallback to deterministic baseline when ML model is untrained.
    """
    project = await verification_repo.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{request.project_id}' not found.",
        )

    links = await verification_repo.get_links(request.project_id)
    spec = None
    if links and links[0].specification_id:
        spec = await requirement_repo.get_specification(links[0].specification_id)

    # Perform impact analysis
    impact = impact_service.analyze_change(
        project=project,
        changed_files=request.changed_files,
        links=links,
        spec=spec,
        file_contents=request.file_contents,
    )
    analysis_repo.save_analysis(impact)

    # Discover concrete tests via engine
    proj_dir = verification_repo.data_dir.parent / "projects" / project.project_id
    engine = VerificationEngine()
    discovered_tests = engine.discover_tests(proj_dir, project.ingested_artifacts)

    report = test_selector.prioritize_tests(
        impact=impact,
        project=project,
        links=links,
        spec=spec,
        strategy=request.strategy,
        discovered_test_nodes=discovered_tests if discovered_tests else None,
    )
    return report


@router.post(
    "/select",
    response_model=TestSelectionReport,
    status_code=status.HTTP_200_OK,
    summary="Select tests under a top-k or execution budget constraint",
)
async def select_tests_for_execution(request: TestSelectionRequest) -> TestSelectionReport:
    """
    Filters prioritized tests into selected and excluded sets with explicit reasons.
    """
    project = await verification_repo.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{request.project_id}' not found.",
        )

    links = await verification_repo.get_links(request.project_id)
    spec = None
    if links and links[0].specification_id:
        spec = await requirement_repo.get_specification(links[0].specification_id)

    impact = impact_service.analyze_change(
        project=project,
        changed_files=request.changed_files,
        links=links,
        spec=spec,
        file_contents=request.file_contents,
    )
    analysis_repo.save_analysis(impact)

    proj_dir = verification_repo.data_dir.parent / "projects" / project.project_id
    engine = VerificationEngine()
    discovered_tests = engine.discover_tests(proj_dir, project.ingested_artifacts)

    selection = test_selector.select_tests(
        impact=impact,
        project=project,
        links=links,
        spec=spec,
        strategy=request.strategy,
        top_k=request.top_k,
        execution_budget_ms=request.execution_budget_ms,
        discovered_test_nodes=discovered_tests if discovered_tests else None,
    )
    return selection


@router.get(
    "/analyses/{analysis_id}",
    response_model=ChangeImpactReport,
    summary="Retrieve previously generated change impact analysis",
)
async def get_analysis_by_id(analysis_id: str) -> ChangeImpactReport:
    """Retrieves stored change impact report by ID."""
    report = analysis_repo.get_analysis(analysis_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis '{analysis_id}' not found.",
        )
    return report


@router.get(
    "/history",
    summary="Retrieve genuine historical test execution observations",
)
async def get_test_history(
    project_id: Optional[str] = Query(default=None),
    include_synthetic: bool = Query(default=False),
) -> List[Dict[str, Any]]:
    """Retrieves collected historical observations used for training and telemetry."""
    obs = history_repo.get_observations(
        project_id=project_id, include_synthetic=include_synthetic
    )
    return [o.model_dump() for o in obs]


@router.post(
    "/history/record",
    summary="Record test results from a completed verification run into history",
)
async def record_verification_run_history(
    run_id: str = Query(..., description="Completed verification run ID")
) -> List[Dict[str, Any]]:
    """Extracts test outcomes from a verification run and persists them as observations."""
    run = await verification_repo.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification run '{run_id}' not found.",
        )
    new_obs = history_repo.record_verification_run(run)
    return [o.model_dump() for o in new_obs]


@router.get(
    "/model/status",
    response_model=ModelStatusReport,
    summary="Inspect predictive model operational telemetry and fallback status",
)
async def get_model_status() -> ModelStatusReport:
    """Returns predictive ML model status, version, training sample count, and fallback behavior."""
    ml_model = PredictiveRegressionModel()
    meta = ml_model.get_metadata()
    return ModelStatusReport(
        model_name=meta.get("model_name", "PredictiveRegressionModel"),
        status=meta.get("status", "not_trained"),
        is_trained=meta.get("is_trained", False),
        version=meta.get("version", "v1.0.0-untrained"),
        resolved_path=meta.get("resolved_path", ""),
        training_sample_count=meta.get("training_sample_count", 0),
        fallback_behavior=meta.get("fallback_behavior", "Deterministic scoring active"),
        notes=meta.get("notes", ""),
        evaluation_metrics=meta.get("evaluation_metrics", {}),
    )


@router.post(
    "/model/train",
    response_model=ModelTrainingReport,
    summary="Train predictive regression model from eligible observations",
)
async def train_predictive_model(request: ModelTrainingRequest) -> ModelTrainingReport:
    """
    Validates observation dataset and trains the scikit-learn regression model.
    If include_synthetic is True and no observations exist, bootstraps pipeline verification samples.
    """
    if request.include_synthetic:
        existing_syn = [o for o in history_repo._observations if o.is_synthetic]
        if not existing_syn:
            history_repo.load_synthetic_test_pipeline_samples(count=40)

    obs = history_repo.get_observations(include_synthetic=request.include_synthetic)
    result = training_pipeline.train_and_persist(
        observations=obs,
        algorithm=request.algorithm,
    )
    return ModelTrainingReport(
        success=result.get("success", False),
        status=result.get("status", "failed"),
        message=result.get("message", ""),
        dataset_summary=result.get("dataset_summary", {}),
        evaluation_metrics=result.get("evaluation_metrics", {}),
    )


@router.post(
    "/model/evaluate",
    summary="Evaluate trained predictive model against held-out observations",
)
async def evaluate_predictive_model(request: ModelEvaluationRequest) -> Dict[str, Any]:
    """
    Evaluates current trained model against held-out observations and compares with baseline.
    """
    ml_model = PredictiveRegressionModel()
    if not ml_model.is_trained:
        return {
            "status": "not_trained",
            "message": "Model is not trained. Cannot perform model evaluation.",
            "metrics": {},
        }

    obs = history_repo.get_observations(include_synthetic=request.include_synthetic)
    eval_res = eval_pipeline.evaluate(
        model=ml_model.model,
        test_observations=obs,
        top_k=request.top_k,
    )
    return eval_res


@router.get(
    "/metrics",
    summary="Aggregate predictive regression telemetry and history summary",
)
async def get_regression_metrics(
    project_id: Optional[str] = Query(default=None)
) -> Dict[str, Any]:
    """Returns combined telemetry including model status and historical observation counts."""
    ml_model = PredictiveRegressionModel()
    summary = history_repo.get_summary(project_id=project_id)
    return {
        "model": ml_model.get_metadata(),
        "history_summary": summary.model_dump(),
    }
