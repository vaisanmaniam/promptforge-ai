from fastapi import APIRouter, HTTPException, status
from ai.prompt_classifier.model import SklearnPromptClassifier
from app.schemas.prompt import (
    AnalyzePromptRequest,
    AnalyzePromptResponse,
    OptimizePromptRequest,
    OptimizePromptResponse,
)
from app.services.prompt_intelligence.ambiguity import AmbiguityDetector
from app.services.prompt_intelligence.components import ComponentDetector
from app.services.prompt_intelligence.optimizer import PromptOptimizer
from app.services.prompt_intelligence.scoring import QualityScorer
from app.services.prompt_intelligence.tokenizer import TokenCounter

router = APIRouter()

# Singletons for service dependencies
classifier = SklearnPromptClassifier()
comp_detector = ComponentDetector()
amb_detector = AmbiguityDetector()
quality_scorer = QualityScorer()
token_counter = TokenCounter()
optimizer = PromptOptimizer()


@router.post(
    "/analyze",
    response_model=AnalyzePromptResponse,
    summary="Analyze Software Engineering Prompt",
    description=(
        "Classifies software task category, detects present and missing components, "
        "identifies ambiguities, and calculates transparent 6-dimension quality scores."
    ),
)
async def analyze_prompt(request: AnalyzePromptRequest) -> AnalyzePromptResponse:
    prompt_text = request.prompt.strip()
    if not prompt_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prompt cannot be empty or contain only whitespace.",
        )

    # 1. Classification
    if request.task_category:
        # User specified override
        probs = classifier.predict_proba(prompt_text)
        from ai.prompt_classifier.base import ClassificationResult
        classification = ClassificationResult(
            predicted_category=request.task_category,
            confidence=1.0,
            probabilities=probs,
            model_name="user_specified_category",
            model_version="manual",
            method="user_override",
            is_baseline=False,
        )
    else:
        classification = classifier.predict(prompt_text)

    # 2. Components & Ambiguities
    comp_report = comp_detector.analyze(prompt_text)
    amb_report = amb_detector.analyze(prompt_text)

    # 3. Quality Evaluation
    quality = quality_scorer.evaluate(
        prompt=prompt_text,
        comp_report=comp_report,
        amb_report=amb_report,
        task_category=classification.predicted_category,
    )

    # 4. Token metrics
    token_count, method, tokenizer_id, is_exact = token_counter.count_tokens(prompt_text)

    return AnalyzePromptResponse(
        task_classification=classification,
        components=comp_report,
        ambiguity=amb_report,
        quality=quality,
        token_count=token_count,
        token_counting_method=method,
        tokenizer_identity=tokenizer_id,
        is_exact_tokens=is_exact,
    )


@router.post(
    "/optimize",
    response_model=OptimizePromptResponse,
    summary="Optimize Software Engineering Prompt",
    description=(
        "Restructures prompt into verifiable software engineering format, "
        "exposes proposed assumptions, generates clarification questions, "
        "and computes before/after quality and token efficiency."
    ),
)
async def optimize_prompt(request: OptimizePromptRequest) -> OptimizePromptResponse:
    prompt_text = request.prompt.strip()
    if not prompt_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prompt cannot be empty or contain only whitespace.",
        )

    # 1. Base Analysis
    if request.task_category:
        from ai.prompt_classifier.base import ClassificationResult
        probs = classifier.predict_proba(prompt_text)
        classification = ClassificationResult(
            predicted_category=request.task_category,
            confidence=1.0,
            probabilities=probs,
            model_name="user_specified_category",
            model_version="manual",
            method="user_override",
            is_baseline=False,
        )
    else:
        classification = classifier.predict(prompt_text)

    orig_comp_report = comp_detector.analyze(prompt_text)
    orig_amb_report = amb_detector.analyze(prompt_text)
    orig_quality = quality_scorer.evaluate(
        prompt=prompt_text,
        comp_report=orig_comp_report,
        amb_report=orig_amb_report,
        task_category=classification.predicted_category,
    )

    # 2. Optimize
    opt_result = optimizer.optimize(
        prompt=prompt_text,
        task_category=classification.predicted_category,
        comp_report=orig_comp_report,
        amb_report=orig_amb_report,
    )

    # 3. Evaluate Optimized Prompt
    opt_comp_report = comp_detector.analyze(opt_result.optimized_prompt)
    opt_amb_report = amb_detector.analyze(opt_result.optimized_prompt)
    opt_quality = quality_scorer.evaluate(
        prompt=opt_result.optimized_prompt,
        comp_report=opt_comp_report,
        amb_report=opt_amb_report,
        task_category=classification.predicted_category,
    )

    # 4. Token Comparison
    token_comparison = token_counter.compare(
        original_text=prompt_text,
        optimized_text=opt_result.optimized_prompt,
        original_score=orig_quality.overall_score,
        optimized_score=opt_quality.overall_score,
    )

    return OptimizePromptResponse(
        optimization=opt_result,
        task_classification=classification,
        original_quality=orig_quality,
        optimized_quality=opt_quality,
        token_analysis=token_comparison,
    )
