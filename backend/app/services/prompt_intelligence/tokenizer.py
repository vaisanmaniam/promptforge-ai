from typing import Optional, Tuple
from pydantic import BaseModel, Field


class TokenAnalysisReport(BaseModel):
    """Token efficiency metrics comparing original and optimized text."""
    original_tokens: int = Field(ge=0)
    optimized_tokens: int = Field(ge=0)
    token_delta: int
    percentage_change: float
    original_quality_per_token: float
    optimized_quality_per_token: float
    counting_method: str = Field(pattern="^(exact_bpe|heuristic_estimate)$")
    tokenizer_identity: str
    is_exact: bool


class TokenCounter:
    """
    Token-counting service with exact BPE encoding via tiktoken
    and graceful heuristic fallback when unconfigured.
    """

    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding_name = encoding_name
        self._tokenizer = None
        self._init_tokenizer()

    def _init_tokenizer(self) -> None:
        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding(self.encoding_name)
        except Exception:
            self._tokenizer = None

    @property
    def is_exact_available(self) -> bool:
        return self._tokenizer is not None

    def count_tokens(self, text: str) -> Tuple[int, str, str, bool]:
        """
        Counts tokens in string.
        Returns: (token_count, counting_method, tokenizer_identity, is_exact)
        """
        if not text:
            return 0, "exact_bpe" if self.is_exact_available else "heuristic_estimate", self.encoding_name, self.is_exact_available

        if self._tokenizer is not None:
            count = len(self._tokenizer.encode(text))
            return count, "exact_bpe", f"tiktoken_{self.encoding_name}", True

        # Heuristic estimation: ~4 characters per token in English text/code
        words = text.split()
        char_estimate = max(1, round(len(text) / 4.0))
        word_estimate = max(1, round(len(words) * 1.3))
        # Blend character and word estimates
        estimate = round((char_estimate + word_estimate) / 2.0)
        return estimate, "heuristic_estimate", "char_word_ratio_v1", False

    def compare(
        self,
        original_text: str,
        optimized_text: str,
        original_score: float = 0.0,
        optimized_score: float = 0.0,
    ) -> TokenAnalysisReport:
        orig_count, method, tokenizer_id, is_exact = self.count_tokens(original_text)
        opt_count, _, _, _ = self.count_tokens(optimized_text)

        delta = opt_count - orig_count
        pct_change = round((delta / max(1, orig_count)) * 100.0, 2) if orig_count > 0 else 0.0

        orig_qpt = round(original_score / max(1, orig_count), 4)
        opt_qpt = round(optimized_score / max(1, opt_count), 4)

        return TokenAnalysisReport(
            original_tokens=orig_count,
            optimized_tokens=opt_count,
            token_delta=delta,
            percentage_change=pct_change,
            original_quality_per_token=orig_qpt,
            optimized_quality_per_token=opt_qpt,
            counting_method=method,
            tokenizer_identity=tokenizer_id,
            is_exact=is_exact,
        )
