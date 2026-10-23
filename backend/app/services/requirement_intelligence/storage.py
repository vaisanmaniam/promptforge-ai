"""
Requirement Specification Persistence Repository.
Provides seamless hybrid persistence:
Attempts SQLAlchemy / PostgreSQL storage when the relational database is available,
and automatically falls back to local structured JSON file storage when PostgreSQL is offline.
Ensures zero runtime failure and full operational resilience.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from sqlalchemy import select
from app.core.logging import logger
from app.db.session import check_database_health, get_async_engine
from app.models.requirement import RequirementItemModel, RequirementSpecificationModel
from app.schemas.requirement import (
    RequirementItem,
    RequirementSpecification,
    SpecificationSummary,
)

# Local fallback directory
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "specifications"


class RequirementRepository:
    """
    Hybrid repository for requirement specifications with automatic SQLite/JSON fallback.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._in_memory_cache: Dict[str, RequirementSpecification] = {}

    async def save_specification(self, spec: RequirementSpecification) -> RequirementSpecification:
        """
        Saves a requirement specification to database if reachable, plus local backup store.
        """
        # Always update memory cache and local JSON file for bulletproof resilience
        self._in_memory_cache[spec.id] = spec
        file_path = self.storage_dir / f"{spec.id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(spec.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write local specification file: {e}")

        # Check database health before attempting PostgreSQL query
        is_healthy, _, _ = await check_database_health()
        if is_healthy:
            try:
                engine = get_async_engine()
                from sqlalchemy.ext.asyncio import AsyncSession
                async with AsyncSession(engine) as session:
                    async with session.begin():
                        # Check existing
                        existing = await session.get(RequirementSpecificationModel, spec.id)
                        if existing:
                            existing.title = spec.title
                            existing.source_prompt = spec.source_prompt
                            existing.task_category = spec.task_category
                            existing.category_breakdown = spec.category_breakdown
                            existing.assumptions = [a.model_dump() for a in spec.assumptions]
                            existing.version = spec.version
                            existing.updated_at = datetime.utcnow()

                            # Delete old items
                            for item in existing.requirements:
                                await session.delete(item)
                        else:
                            spec_model = RequirementSpecificationModel(
                                id=spec.id,
                                title=spec.title,
                                source_prompt=spec.source_prompt,
                                task_category=spec.task_category,
                                category_breakdown=spec.category_breakdown,
                                assumptions=[a.model_dump() for a in spec.assumptions],
                                version=spec.version,
                            )
                            session.add(spec_model)

                        # Add items
                        for req in spec.requirements:
                            item_model = RequirementItemModel(
                                id=f"{spec.id}:{req.id}",
                                spec_id=spec.id,
                                req_code=req.id,
                                title=req.title,
                                description=req.description,
                                category=req.category.value,
                                priority=req.priority.value,
                                status=req.status.value,
                                source_text=req.source_text,
                                assumptions=[a.model_dump() for a in req.assumptions],
                                acceptance_criteria=[ac.model_dump() for ac in req.acceptance_criteria],
                                verification_state=req.verification_state.value,
                                depends_on=req.depends_on,
                                refines=req.refines,
                            )
                            session.add(item_model)
                        await session.commit()
            except Exception as exc:
                logger.warning(f"PostgreSQL persistence skipped due to error: {exc}")

        return spec

    async def get_specification(self, spec_id: str) -> Optional[RequirementSpecification]:
        """
        Retrieves a requirement specification by ID from memory, DB, or disk.
        """
        # 1. In-memory check
        if spec_id in self._in_memory_cache:
            return self._in_memory_cache[spec_id]

        # 2. Local file check
        file_path = self.storage_dir / f"{spec_id}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                spec = RequirementSpecification.model_validate(data)
                self._in_memory_cache[spec_id] = spec
                return spec
            except Exception as e:
                logger.warning(f"Failed to read local file {file_path}: {e}")

        # 3. Database check if available
        is_healthy, _, _ = await check_database_health()
        if is_healthy:
            try:
                engine = get_async_engine()
                from sqlalchemy.ext.asyncio import AsyncSession
                from sqlalchemy.orm import selectinload
                async with AsyncSession(engine) as session:
                    query = (
                        select(RequirementSpecificationModel)
                        .where(RequirementSpecificationModel.id == spec_id)
                        .options(selectinload(RequirementSpecificationModel.requirements))
                    )
                    result = await session.execute(query)
                    spec_model = result.scalar_one_or_none()
                    if spec_model:
                        req_items = []
                        for m in spec_model.requirements:
                            req_items.append(
                                RequirementItem(
                                    id=m.req_code,
                                    title=m.title,
                                    description=m.description,
                                    category=m.category,
                                    priority=m.priority,
                                    status=m.status,
                                    source_text=m.source_text,
                                    assumptions=m.assumptions or [],
                                    acceptance_criteria=m.acceptance_criteria or [],
                                    verification_state=m.verification_state,
                                    depends_on=m.depends_on or [],
                                    refines=m.refines or [],
                                )
                            )
                        spec = RequirementSpecification(
                            id=spec_model.id,
                            title=spec_model.title,
                            source_prompt=spec_model.source_prompt,
                            task_category=spec_model.task_category,
                            category_breakdown=spec_model.category_breakdown or {},
                            requirements=req_items,
                            assumptions=spec_model.assumptions or [],
                            created_at=spec_model.created_at.isoformat() + "Z",
                            updated_at=spec_model.updated_at.isoformat() + "Z",
                            version=spec_model.version,
                        )
                        self._in_memory_cache[spec_id] = spec
                        return spec
            except Exception as exc:
                logger.warning(f"Database fetch failed: {exc}")

        return None

    async def list_specifications(self) -> List[SpecificationSummary]:
        """
        Lists all specifications currently stored.
        """
        summaries: Dict[str, SpecificationSummary] = {}

        # 1. Disk scan
        if self.storage_dir.exists():
            for f in self.storage_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    spec_id = data.get("id")
                    if spec_id:
                        summaries[spec_id] = SpecificationSummary(
                            id=spec_id,
                            title=data.get("title", "Untitled Specification"),
                            task_category=data.get("task_category"),
                            total_requirements=len(data.get("requirements", [])),
                            created_at=data.get("created_at", datetime.utcnow().isoformat()),
                            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
                            version=data.get("version", 1),
                        )
                except Exception:
                    pass

        # 2. Database scan if healthy
        is_healthy, _, _ = await check_database_health()
        if is_healthy:
            try:
                engine = get_async_engine()
                from sqlalchemy.ext.asyncio import AsyncSession
                from sqlalchemy.orm import selectinload
                async with AsyncSession(engine) as session:
                    stmt = select(RequirementSpecificationModel).options(
                        selectinload(RequirementSpecificationModel.requirements)
                    )
                    result = await session.execute(stmt)
                    for row in result.scalars():
                        summaries[row.id] = SpecificationSummary(
                            id=row.id,
                            title=row.title,
                            task_category=row.task_category,
                            total_requirements=len(row.requirements),
                            created_at=row.created_at.isoformat() + "Z",
                            updated_at=row.updated_at.isoformat() + "Z",
                            version=row.version,
                        )
            except Exception as exc:
                logger.warning(f"Database list failed: {exc}")

        # Return sorted by updated_at descending
        items = list(summaries.values())
        items.sort(key=lambda s: s.updated_at, reverse=True)
        return items
