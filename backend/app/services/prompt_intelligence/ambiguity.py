import re
from typing import Dict, List
from pydantic import BaseModel, Field


class AmbiguityFinding(BaseModel):
    """Specific ambiguity marker identified in the prompt."""
    term: str = Field(description="Matched ambiguous term or phrase")
    category: str = Field(description="Category of ambiguity, e.g. 'vague_metric', 'unspecified_choice'")
    explanation: str = Field(description="Why this phrase creates implementation risk")
    clarification_question: str = Field(description="Recommended question to resolve ambiguity")


class AmbiguityReport(BaseModel):
    """Summary of ambiguity analysis."""
    has_ambiguity: bool = Field(description="True if any significant ambiguity was flagged")
    findings: List[AmbiguityFinding] = Field(default_factory=list)
    ambiguity_count: int = Field(default=0)


AMBIGUITY_RULES = [
    {
        "pattern": r"\b(fast|blazing(\s+fast)?|speedy|high\s+performance)\b",
        "category": "vague_performance",
        "explanation": "'Fast' is an unmeasurable subjective claim without latency or throughput SLA.",
        "question": "What is the concrete latency budget (e.g., p99 < 50ms) or throughput requirement (e.g., 500 RPS)?",
    },
    {
        "pattern": r"\b(secure|securely|bulletproof)\b",
        "category": "vague_security",
        "explanation": "'Secure' does not define specific threat models, authentication schemes, or standards.",
        "question": "What specific security mechanisms are required (e.g., OAuth2 with JWT, AES-256 encryption, RBAC)?",
    },
    {
        "pattern": r"\b(scalable|cloud-?ready|enterprise)\b",
        "category": "vague_scalability",
        "explanation": "'Scalable' lacks concurrency expectations, data volume targets, or distributed system specs.",
        "question": "What concurrent user count, database size, or horizontal scaling target should be supported?",
    },
    {
        "pattern": r"\b(user-?friendly|intuitive|clean\s+ui|modern)\b",
        "category": "vague_usability",
        "explanation": "Subjective UI/UX qualifier without wireframes, accessibility requirements, or component standards.",
        "question": "Which design system, WCAG accessibility standard, or UI framework components should be used?",
    },
    {
        "pattern": r"\b(etc\.?|and\s+so\s+on|and\s+more|stuff|things)\b",
        "category": "open_ended_scope",
        "explanation": "'Etc.' creates unbounded scope creep and leaves functional requirements open to interpretation.",
        "question": "Could you list all required items explicitly rather than using 'etc.'?",
    },
    {
        "pattern": r"\b(good|proper|appropriate|reasonable|normal|standard)\b",
        "category": "subjective_quality",
        "explanation": "Relative quality descriptor that fails to define specific acceptance criteria.",
        "question": "What concrete validation rules or standards define what is considered 'proper' in this context?",
    },
    {
        "pattern": r"\b(some\s+(tests?|code|functions?|data)|a\s+few)\b",
        "category": "unspecified_quantity",
        "explanation": "Ambiguous quantity that does not specify test coverage or functionality scope.",
        "question": "Which specific scenarios, edge cases, or test cases should be covered?",
    },
    {
        "pattern": r"\b(any\s+(language|database|framework)|whichever|you\s+choose|up\s+to\s+you)\b",
        "category": "unspecified_technology",
        "explanation": "Unconstrained architectural decision delegated to inference without system context.",
        "question": "Which programming language, database, or runtime environment matches your existing stack?",
    },
]


class AmbiguityDetector:
    """Detects subjective, open-ended, and unquantified terms in prompts."""

    def __init__(self):
        self.rules = AMBIGUITY_RULES

    def analyze(self, prompt: str) -> AmbiguityReport:
        text = prompt.strip()
        findings: List[AmbiguityFinding] = []
        seen_terms = set()

        if not text:
            return AmbiguityReport(has_ambiguity=False, findings=[], ambiguity_count=0)

        for rule in self.rules:
            matches = re.findall(rule["pattern"], text, re.IGNORECASE)
            if matches:
                term = matches[0] if isinstance(matches[0], str) else matches[0][0]
                term_lower = term.lower()
                if term_lower not in seen_terms:
                    seen_terms.add(term_lower)
                    findings.append(
                        AmbiguityFinding(
                            term=term,
                            category=rule["category"],
                            explanation=rule["explanation"],
                            clarification_question=rule["question"],
                        )
                    )

        return AmbiguityReport(
            has_ambiguity=len(findings) > 0,
            findings=findings,
            ambiguity_count=len(findings),
        )
