"""
SQLAlchemy database models for Predictive Regression Testing.
Stores historical test execution outcomes and change impact analyses.
"""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, JSON
from app.models.requirement import Base


class RegressionAnalysisModel(Base):
    """Database model for a change impact analysis run."""
    __tablename__ = "regression_analyses"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    changed_files = Column(JSON, default=list)
    directly_affected_requirements = Column(JSON, default=list)
    downstream_affected_requirements = Column(JSON, default=list)
    max_blast_radius_depth = Column(Integer, default=0)
    evidence_disclosures = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestExecutionHistoryModel(Base):
    """Database model for historical test execution observations."""
    __tablename__ = "test_execution_history"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    change_id = Column(String(64), nullable=False, index=True)
    test_id = Column(String(255), nullable=False, index=True)
    outcome = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Float, default=0.0)
    label_provenance = Column(String(128), default="docker_verification_run")
    is_synthetic = Column(Boolean, default=False)
    features = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
