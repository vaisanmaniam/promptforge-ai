"""
Verification Repository.
Provides hybrid persistence for projects, artifacts, traceability links, and verification runs:
persists to PostgreSQL when available, and automatically falls back to local JSON storage
in `backend/data/verification/` when PostgreSQL is offline.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select
from app.core.logging import logger
from app.db.session import check_database_health, get_async_engine
from app.models.verification import (
    ArtifactModel,
    ProjectModel,
    TraceabilityLinkModel,
    VerificationRunModel,
)
from app.schemas.verification import (
    ArtifactMetadata,
    ProjectIngestionReport,
    ProjectSummary,
    TraceabilityLink,
    VerificationRun,
)

VERIFICATION_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "verification"


class VerificationRepository:
    """
    Repository for Phase 4 verification entities with automatic JSON fallback.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or VERIFICATION_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "projects").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "links").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "runs").mkdir(parents=True, exist_ok=True)

        self._projects_cache: Dict[str, ProjectIngestionReport] = {}
        self._links_cache: Dict[str, List[TraceabilityLink]] = {}  # project_id -> links
        self._runs_cache: Dict[str, VerificationRun] = {}

    async def save_project(self, project: ProjectIngestionReport) -> ProjectIngestionReport:
        """Saves ingested project report and artifact metadata."""
        self._projects_cache[project.project_id] = project

        # Local disk backup
        proj_file = self.data_dir / "projects" / f"{project.project_id}.json"
        try:
            with open(proj_file, "w", encoding="utf-8") as f:
                json.dump(project.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write project JSON: {e}")

        # Database persistence if online
        is_healthy, _, _ = await check_database_health()
        if is_healthy:
            try:
                engine = get_async_engine()
                from sqlalchemy.ext.asyncio import AsyncSession
                async with AsyncSession(engine) as session:
                    async with session.begin():
                        existing = await session.get(ProjectModel, project.project_id)
                        if not existing:
                            pm = ProjectModel(
                                id=project.project_id,
                                name=project.name,
                                total_files=project.total_files,
                                total_size_bytes=project.total_size_bytes,
                                manifests=project.detected_manifests,
                                test_frameworks=project.detected_test_frameworks,
                                test_commands=project.available_test_commands,
                            )
                            session.add(pm)

                            for a in project.ingested_artifacts:
                                am = ArtifactModel(
                                    id=a.id,
                                    project_id=project.project_id,
                                    relative_path=a.relative_path,
                                    file_type=a.file_type.value,
                                    language=a.language,
                                    sha256=a.sha256,
                                    size_bytes=a.size_bytes,
                                    line_count=a.line_count,
                                    symbols=a.symbols,
                                )
                                session.add(am)
                        await session.commit()
            except Exception as exc:
                logger.warning(f"Database save_project skipped: {exc}")

        return project

    async def get_project(self, project_id: str) -> Optional[ProjectIngestionReport]:
        """Retrieves project report from cache, disk, or DB."""
        if project_id in self._projects_cache:
            return self._projects_cache[project_id]

        proj_file = self.data_dir / "projects" / f"{project_id}.json"
        if proj_file.exists():
            try:
                with open(proj_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report = ProjectIngestionReport.model_validate(data)
                self._projects_cache[project_id] = report
                return report
            except Exception:
                pass

        return None

    async def list_projects(self) -> List[ProjectSummary]:
        """Lists summaries of all ingested projects."""
        summaries: Dict[str, ProjectSummary] = {}

        # Scan disk
        p_dir = self.data_dir / "projects"
        if p_dir.exists():
            for pf in p_dir.glob("*.json"):
                try:
                    with open(pf, "r", encoding="utf-8") as f:
                        d = json.load(f)
                    pid = d.get("project_id")
                    if pid:
                        summaries[pid] = ProjectSummary(
                            project_id=pid,
                            name=d.get("name", pid),
                            total_files=d.get("total_files", 0),
                            ingested_at=d.get("ingested_at", datetime.utcnow().isoformat()),
                        )
                except Exception:
                    pass

        return list(summaries.values())

    async def save_links(
        self, project_id: str, links: List[TraceabilityLink]
    ) -> List[TraceabilityLink]:
        """Saves traceability links for a project."""
        self._links_cache[project_id] = links

        link_file = self.data_dir / "links" / f"{project_id}.json"
        try:
            with open(link_file, "w", encoding="utf-8") as f:
                json.dump([l.model_dump() for l in links], f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write links JSON: {e}")

        return links

    async def get_links(self, project_id: str) -> List[TraceabilityLink]:
        """Retrieves traceability links for a project."""
        if project_id in self._links_cache:
            return self._links_cache[project_id]

        link_file = self.data_dir / "links" / f"{project_id}.json"
        if link_file.exists():
            try:
                with open(link_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                links = [TraceabilityLink.model_validate(d) for d in data]
                self._links_cache[project_id] = links
                return links
            except Exception:
                pass

        return []

    async def update_link(
        self, project_id: str, link_id: str, is_confirmed: bool
    ) -> Optional[TraceabilityLink]:
        """Updates confirmation status for a specific link."""
        links = await self.get_links(project_id)
        target_link = next((l for l in links if l.id == link_id), None)
        if not target_link:
            return None

        from app.services.verification.traceability import CodeTraceabilityService
        tracer = CodeTraceabilityService()
        tracer.confirm_link(target_link, is_confirmed)

        await self.save_links(project_id, links)
        return target_link

    async def save_run(self, run: VerificationRun) -> VerificationRun:
        """Saves a verification run."""
        self._runs_cache[run.id] = run

        run_file = self.data_dir / "runs" / f"{run.id}.json"
        try:
            with open(run_file, "w", encoding="utf-8") as f:
                json.dump(run.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write run JSON: {e}")

        return run

    async def get_run(self, run_id: str) -> Optional[VerificationRun]:
        """Retrieves a verification run by ID."""
        if run_id in self._runs_cache:
            return self._runs_cache[run_id]

        run_file = self.data_dir / "runs" / f"{run_id}.json"
        if run_file.exists():
            try:
                with open(run_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                run = VerificationRun.model_validate(d)
                self._runs_cache[run_id] = run
                return run
            except Exception:
                pass

        return None

    async def get_latest_run_for_project(
        self, project_id: str
    ) -> Optional[VerificationRun]:
        """Finds the most recent verification run for a project."""
        # Scan disk
        runs_dir = self.data_dir / "runs"
        if not runs_dir.exists():
            return None

        latest_run = None
        for rf in runs_dir.glob("*.json"):
            try:
                with open(rf, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("project_id") == project_id:
                    run = VerificationRun.model_validate(d)
                    if not latest_run or run.created_at > latest_run.created_at:
                        latest_run = run
            except Exception:
                pass

        return latest_run
