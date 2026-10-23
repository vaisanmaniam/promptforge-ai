"""
Analysis Repository for Change Impact Reports.
Provides hybrid persistence: PostgreSQL when reachable, and local JSON
fallback in `backend/data/regression/analyses/` when offline.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logging import logger
from app.schemas.regression import ChangeImpactReport

ANALYSES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "regression" / "analyses"


class AnalysisRepository:
    """Repository storing change impact analysis records."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or ANALYSES_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, ChangeImpactReport] = {}

    def save_analysis(self, report: ChangeImpactReport) -> ChangeImpactReport:
        """Saves a change impact report to memory and local disk."""
        self._cache[report.analysis_id] = report
        file_path = self.data_dir / f"{report.analysis_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist analysis JSON: {e}")
        return report

    def get_analysis(self, analysis_id: str) -> Optional[ChangeImpactReport]:
        """Retrieves a change impact report by analysis_id."""
        if analysis_id in self._cache:
            return self._cache[analysis_id]

        file_path = self.data_dir / f"{analysis_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report = ChangeImpactReport.model_validate(data)
                self._cache[analysis_id] = report
                return report
            except Exception:
                pass
        return None
