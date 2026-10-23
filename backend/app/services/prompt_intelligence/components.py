import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ComponentFinding(BaseModel):
    """Detailed evidence for a single software engineering component."""
    component: str = Field(description="Component name")
    status: str = Field(pattern="^(detected|missing|uncertain)$", description="'detected', 'missing', or 'uncertain'")
    evidence: Optional[str] = Field(default=None, description="Matched pattern, phrase, or rationale")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the finding")
    detection_method: str = Field(default="deterministic_pattern", description="Method utilized")


class ComponentDetectionReport(BaseModel):
    """Aggregated component analysis of a prompt."""
    detected: List[str] = Field(default_factory=list, description="List of detected component names")
    missing: List[str] = Field(default_factory=list, description="List of missing component names")
    uncertain: List[str] = Field(default_factory=list, description="List of uncertain component names")
    findings: Dict[str, ComponentFinding] = Field(default_factory=dict, description="Detailed component findings")


COMPONENT_PATTERNS = {
    "objective": [
        r"\b(implement|write|create|build|develop|generate|fix|debug|review|audit|test|refactor|design|configure|document|deploy)\b",
        r"\b(function to|class for|script to|endpoint for|algorithm that|query to)\b",
    ],
    "context": [
        r"\b(in\s+my|currently|production|legacy|existing|monolith|microservice|when\s+traversing|table\s+\w+\s+has|scenario|background|architecture)\b",
        r"\b(since\s+yesterday|after\s+adding|environment|context)\b",
    ],
    "target_technology": [
        r"\b(python|typescript|javascript|react|vue|angular|fastapi|flask|django|express(\.js)?|spring(\s+boot)?|go|golang|rust|java|c\+\+|c#|\.net|node(\.js)?|ruby|php|kotlin|swift)\b",
        r"\b(postgresql|postgres|mysql|sqlite|redis|mongodb|cassandra|snowflake|bigquery)\b",
        r"\b(docker|kubernetes|k8s|helm|terraform|ansible|nginx|prometheus|aws|gcp|azure|kafka|rabbitmq|git|bash)\b",
    ],
    "inputs": [
        r"\b(accepts?|takes?|parameters?|args?|arguments?|inputs?|payload|body|query\s+params?|headers?|props?|schema)\b",
        r"\b(columns?|fields?|data\s+structure|format|signature|json\s+with)\b",
    ],
    "expected_outputs": [
        r"\b(returns?|expected\s+output|produces?|yielding|response\s+(code|body)|json\s+response)\b",
        r"\b(200\s+ok|201\s+created|204\s+no\s+content|400\s+bad\s+request|404\s+not\s+found|500\s+internal)\b",
        r"\b(dictionary|array|list\s+of|boolean|tuple|checksum|file|artifact)\b",
    ],
    "functional_requirements": [
        r"\b(should|must|needs\s+to|calculate|validate|convert|transform|traverse|merge|filter|parse|compress|synchronize)\b",
        r"\b(handle|support|process|update|insert|delete|fetch|stream)\b",
    ],
    "constraints": [
        r"\b(o\(1\)|o\(n\)|time\s+complexity|space\s+complexity|memory\s+limit|timeout|thread-safe|concurrency)\b",
        r"\b(without\s+using|no\s+built-in|under\s+\d+\s*(mb|gb|ms|s)|max\s+\d+|rate\s+limit|restriction|non-blocking)\b",
    ],
    "security_requirements": [
        r"\b(auth(entication)?|authoriz(ation)?|jwt|token|bcrypt|hash|password|salt|oauth2?)\b",
        r"\b(sql\s+injection|xss|csrf|cors|sanitiz|encrypt(ion)?|aes-?256|ssl|tls|non-root|secret|permission)\b",
    ],
    "testing_requirements": [
        r"\b(unit\s+tests?|pytest|jest|xunit|junit|integration\s+tests?|e2e\s+tests?|playwright|mock(ing)?)\b",
        r"\b(assert(ion)?|coverage|fuzz(ing)?|hypothesis|benchmark|test\s+cases?|table-driven)\b",
    ],
    "acceptance_criteria": [
        r"\b(acceptance\s+criteria|definition\s+of\s+done|verify\s+that|ensure\s+that|must\s+pass|expected\s+behavior)\b",
        r"\b(throws?\s+error\s+if|raises?\s+\w+error\s+when|asserts?\s+that)\b",
    ],
}


class ComponentDetector:
    """
    Transparent multi-label software engineering component detector.
    Provides explainable evidence and explicit uncertainty.
    """

    def __init__(self):
        self.patterns = COMPONENT_PATTERNS

    def analyze(self, prompt: str) -> ComponentDetectionReport:
        text = prompt.strip()
        detected: List[str] = []
        missing: List[str] = []
        uncertain: List[str] = []
        findings: Dict[str, ComponentFinding] = {}

        if not text:
            for comp in self.patterns.keys():
                findings[comp] = ComponentFinding(
                    component=comp,
                    status="missing",
                    evidence="Prompt is empty",
                    confidence=1.0,
                )
                missing.append(comp)
            return ComponentDetectionReport(detected=[], missing=missing, uncertain=[], findings=findings)

        for comp, regexes in self.patterns.items():
            matches: List[str] = []
            for pat in regexes:
                found = re.findall(pat, text, re.IGNORECASE)
                if found:
                    for item in found:
                        if isinstance(item, tuple):
                            matches.append(item[0])
                        else:
                            matches.append(item)

            if len(matches) >= 2:
                findings[comp] = ComponentFinding(
                    component=comp,
                    status="detected",
                    evidence=f"Matched indicators: {', '.join(sorted(list(set(matches)))[:3])}",
                    confidence=0.9,
                    detection_method="deterministic_pattern",
                )
                detected.append(comp)
            elif len(matches) == 1:
                findings[comp] = ComponentFinding(
                    component=comp,
                    status="detected",
                    evidence=f"Indicator: {matches[0]}",
                    confidence=0.75,
                    detection_method="deterministic_pattern",
                )
                detected.append(comp)
            else:
                findings[comp] = ComponentFinding(
                    component=comp,
                    status="missing",
                    evidence=f"No indicators matching {comp} patterns",
                    confidence=0.85,
                    detection_method="deterministic_pattern",
                )
                missing.append(comp)

        return ComponentDetectionReport(
            detected=detected,
            missing=missing,
            uncertain=uncertain,
            findings=findings,
        )
