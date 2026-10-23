import re
from typing import Any, Dict
from ai.prompt_classifier.base import BasePromptClassifier, ClassificationResult

TASK_KEYWORDS = {
    "sql_generation": [
        r"\bsql\b", r"\bselect\b", r"\bfrom\s+\w+", r"\bwhere\b", r"\bjoin\b",
        r"\bgroup\s+by\b", r"\border\s+by\b", r"\bcte\b", r"\bwindow\s+function",
        r"\bdense_rank\b", r"\bquery\b", r"\btable\b", r"\bdatabase\s+schema\b",
        r"\bpostgresql\b", r"\bmysql\b", r"\bsnowflake\b", r"\bbigquery\b",
        r"\bjsonb\b", r"\bddl\b", r"\bexplain\s+analyze\b",
    ],
    "test_generation": [
        r"\bunit\s+tests?\b", r"\bpytest\b", r"\bjest\b", r"\bmock\b",
        r"\bassert\b", r"\btest\s+cases?\b", r"\bintegration\s+tests?\b",
        r"\be2e\s+test", r"\bplaywright\b", r"\bfuzz\s+test", r"\bhypothesis\b",
        r"\bxunit\b", r"\bbenchmark\s+tests?\b", r"\bcontract\s+test",
    ],
    "debugging": [
        r"\bfix\b", r"\berror\b", r"\bbug\b", r"\bcrash\b", r"\bexception\b",
        r"\btraceback\b", r"\bissue\b", r"\bpanic\b", r"\bnullpointer",
        r"\btypeerror\b", r"\brecursionerror\b", r"\bmemory\s+leak\b",
        r"\binfinite\s+loop\b", r"\bdead-?lock\b", r"\bcors\s+policy\b",
        r"\btroubleshoot\b", r"\bwhy\s+is\s+my\b",
    ],
    "code_review": [
        r"\breview\b", r"\baudit\b", r"\bsecurity\s+audit\b", r"\bcode\s+smell",
        r"\bsolid\s+principles\b", r"\bclean\s+code\b", r"\bpull\s+request\b",
        r"\bpr\b", r"\bperformance\s+review\b", r"\bgive\s+feedback\b",
        r"\ba11y\b", r"\banti-?patterns?\b", r"\breentrancy\b",
    ],
    "api_development": [
        r"\bapi\b", r"\bendpoint\b", r"\brest\b", r"\bpost\s+/", r"\bget\s+/",
        r"\bput\s+/", r"\bdelete\s+/", r"\bfastapi\b", r"\bexpress\.js\b",
        r"\bcontroller\b", r"\bgraphql\b", r"\bmutation\b", r"\bwebsocket\b",
        r"\bgrpc\b", r"\bwebhook\b", r"\brate\s+limit",
    ],
    "devops": [
        r"\bdocker\b", r"\bdockerfile\b", r"\bkubernetes\b", r"\bk8s\b",
        r"\bhelm\b", r"\bterraform\b", r"\bci/cd\b", r"\bgithub\s+actions\b",
        r"\bworkflow\b", r"\bnginx\b", r"\bansible\b", r"\bsystemd\b",
        r"\bprometheus\b", r"\bdeploy\b", r"\baws\s+s3\b", r"\bcloudformation\b",
    ],
    "documentation": [
        r"\bdocument\b", r"\bdocstrings?\b", r"\breadme(\.md)?\b", r"\bmarkdown\b",
        r"\bjsdoc\b", r"\bchangelog\b", r"\bopenapi\b", r"\bswagger\b",
        r"\barchitecture\s+decision\b", r"\badr\b", r"\bonboarding\s+guide\b",
        r"\buser\s+documentation\b", r"\brelease\s+notes\b", r"\bsemver\b",
    ],
    "code_generation": [
        r"\bimplement\b", r"\bwrite\s+(a\s+)?(function|class|script|code|algorithm)\b",
        r"\bcreate\s+(a\s+)?(function|class|script|algorithm)\b",
        r"\bbuild\s+(a\s+)?(scraper|utility|parser)\b",
        r"\blru\s+cache\b", r"\bbinary\s+search\s+tree\b", r"\bdijkstra\b",
        r"\bdebounce\b", r"\bhash\s+map\b", r"\btwo\s+sum\b",
    ],
}


class RuleBasedClassifier(BasePromptClassifier):
    """
    Deterministic rule-based keyword & regex matching classifier.
    Acts as a verifiable baseline and fallback when ML model weights are unavailable.
    """

    def __init__(self, version: str = "v1.0.0-rules"):
        self.version = version

    def predict_proba(self, prompt: str) -> Dict[str, float]:
        text = prompt.lower()
        scores: Dict[str, float] = {}

        for category, patterns in TASK_KEYWORDS.items():
            count = 0
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                count += len(matches)
            scores[category] = float(count)

        total = sum(scores.values())
        if total == 0:
            # Uniform prior across all 8 classes
            num_classes = len(TASK_KEYWORDS)
            return {k: round(1.0 / num_classes, 4) for k in TASK_KEYWORDS}

        return {k: round(v / total, 4) for k, v in scores.items()}

    def predict(self, prompt: str) -> ClassificationResult:
        probs = self.predict_proba(prompt)
        best_cat = max(probs, key=probs.get)
        confidence = probs[best_cat]

        return ClassificationResult(
            predicted_category=best_cat,
            confidence=confidence,
            probabilities=probs,
            model_name="rule_based_keyword_matcher",
            model_version=self.version,
            method="rule_based_fallback",
            is_baseline=True,
        )

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "RuleBasedClassifier",
            "version": self.version,
            "type": "heuristic_regex",
            "categories_supported": list(TASK_KEYWORDS.keys()),
        }
