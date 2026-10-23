import pytest
from app.services.prompt_intelligence.ambiguity import AmbiguityDetector
from app.services.prompt_intelligence.components import ComponentDetector
from app.services.prompt_intelligence.optimizer import PromptOptimizer
from app.services.prompt_intelligence.scoring import QualityScorer
from app.services.prompt_intelligence.tokenizer import TokenCounter


def test_component_detector():
    """Verify component detector identifies explicit and missing elements."""
    detector = ComponentDetector()

    complete_prompt = (
        "Implement a thread-safe LRU cache in Python using a doubly linked list. "
        "Accepts capacity parameter, returns value on get(key), raises KeyError if missing. "
        "Must achieve O(1) time complexity."
    )
    report = detector.analyze(complete_prompt)

    assert "objective" in report.detected
    assert "target_technology" in report.detected
    assert "inputs" in report.detected
    assert "expected_outputs" in report.detected
    assert "constraints" in report.detected
    assert len(report.missing) > 0  # e.g., security_requirements missing

    empty_report = detector.analyze("")
    assert len(empty_report.detected) == 0
    assert len(empty_report.missing) == 10


def test_ambiguity_detector():
    """Verify ambiguity detector flags subjective and open-ended words."""
    detector = AmbiguityDetector()

    ambiguous_prompt = "Build a fast and secure web application with users, etc."
    report = detector.analyze(ambiguous_prompt)

    assert report.has_ambiguity is True
    assert report.ambiguity_count >= 3
    terms = [f.term.lower() for f in report.findings]
    assert any("fast" in t for t in terms)
    assert any("secure" in t for t in terms)
    assert any("etc" in t for t in terms)

    clean_prompt = (
        "Write a PostgreSQL query to count active users from table users "
        "where status = 'active' and created_at >= '2026-01-01'."
    )
    clean_report = detector.analyze(clean_prompt)
    assert clean_report.has_ambiguity is False


def test_quality_scorer():
    """Verify quality scoring weights, dimensions, and score calculations."""
    scorer = QualityScorer()
    comp_detector = ComponentDetector()
    amb_detector = AmbiguityDetector()

    high_quality_prompt = (
        "Implement a thread-safe LRU cache in Python using a doubly linked list and hash map. "
        "Accepts an integer capacity parameter. Methods include get(key) returning the value, "
        "and put(key, value). Raises KeyError when key is not found. Must have O(1) time complexity."
    )
    comp_high = comp_detector.analyze(high_quality_prompt)
    amb_high = amb_detector.analyze(high_quality_prompt)
    assessment_high = scorer.evaluate(high_quality_prompt, comp_high, amb_high, "code_generation")

    assert assessment_high.overall_score >= 65.0
    assert len(assessment_high.dimension_scores) == 6
    assert assessment_high.dimension_scores["clarity"].score > 70.0

    low_quality_prompt = "make app fast and good"
    comp_low = comp_detector.analyze(low_quality_prompt)
    amb_low = amb_detector.analyze(low_quality_prompt)
    assessment_low = scorer.evaluate(low_quality_prompt, comp_low, amb_low, "code_generation")

    assert assessment_low.overall_score < 40.0
    assert len(assessment_low.recommendations) > 0


def test_quality_scorer_invalid_weights():
    """Verify scorer rejects weights that do not sum to 1.0."""
    invalid_weights = {"clarity": 0.5, "context": 0.2}
    with pytest.raises(ValueError, match="Quality weights must sum to 1.0"):
        QualityScorer(weights=invalid_weights)


def test_prompt_optimizer():
    """Verify optimizer preserves original objective and exposes assumptions."""
    optimizer = PromptOptimizer()
    comp_detector = ComponentDetector()
    amb_detector = AmbiguityDetector()

    raw_prompt = "Create an API endpoint for user registration."
    comp_rep = comp_detector.analyze(raw_prompt)
    amb_rep = amb_detector.analyze(raw_prompt)

    opt_result = optimizer.optimize(raw_prompt, "api_development", comp_rep, amb_rep)

    # 1. Objective preservation
    assert raw_prompt in opt_result.optimized_prompt
    assert opt_result.original_prompt == raw_prompt

    # 2. Section addition
    assert "### 1. Objective" in opt_result.optimized_prompt
    assert "### 2. Technical Context & Stack" in opt_result.optimized_prompt
    assert len(opt_result.added_sections) >= 4

    # 3. Explicit assumption exposure
    assert len(opt_result.assumptions) > 0
    assert any("FastAPI" in a for a in opt_result.assumptions)
    assert "[PROPOSED ASSUMPTION" in opt_result.optimized_prompt


def test_token_counter():
    """Verify token counting and comparison metrics."""
    counter = TokenCounter()

    count, method, tok_id, is_exact = counter.count_tokens("Hello world from PromptForge AI")
    assert count > 0
    assert method in ("exact_bpe", "heuristic_estimate")
    if is_exact:
        assert method == "exact_bpe"
        assert "tiktoken" in tok_id

    # Comparison test
    comp = counter.compare("short prompt", "much longer optimized prompt with multiple detailed sections", 50.0, 85.0)
    assert comp.optimized_tokens > comp.original_tokens
    assert comp.token_delta > 0
    assert comp.percentage_change > 0
    assert comp.optimized_quality_per_token > 0
