"""
SQLAlchemy models for requirements and traceability persistence.
Supports relational PostgreSQL schema with JSON fields for structured metadata.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class RequirementSpecificationModel(Base):
    """Database model for an entire requirement specification."""
    __tablename__ = "requirement_specifications"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source_prompt = Column(Text, nullable=False)
    task_category = Column(String(64), nullable=True)
    category_breakdown = Column(JSON, default=dict)
    assumptions = Column(JSON, default=list)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requirements = relationship(
        "RequirementItemModel",
        back_populates="specification",
        cascade="all, delete-orphan",
        order_by="RequirementItemModel.req_code",
    )


class RequirementItemModel(Base):
    """Database model for a single structured requirement item."""
    __tablename__ = "requirement_items"

    id = Column(String(128), primary_key=True, index=True)  # spec_id + ":" + req_code
    spec_id = Column(String(64), ForeignKey("requirement_specifications.id"), nullable=False, index=True)
    req_code = Column(String(32), nullable=False, index=True)  # e.g. REQ-001
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(64), nullable=False, index=True)
    priority = Column(String(32), default="medium")
    status = Column(String(32), default="explicit")
    source_text = Column(Text, nullable=True)
    assumptions = Column(JSON, default=list)
    acceptance_criteria = Column(JSON, default=list)
    verification_state = Column(String(32), default="unverified")
    depends_on = Column(JSON, default=list)
    refines = Column(JSON, default=list)

    specification = relationship("RequirementSpecificationModel", back_populates="requirements")
