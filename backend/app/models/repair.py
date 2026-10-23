"""
SQLAlchemy database models for Failure-Guided Automated Code Repair.
Persists failure analyses, repair proposals, approval states, and audit trails.
"""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from app.models.requirement import Base


class FailureAnalysisModel(Base):
    """Database model for an analyzed verification test failure."""
    __tablename__ = "failure_analyses"

    id = Column(String(64), primary_key=True, index=True)
    run_id = Column(String(64), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    test_id = Column(String(255), nullable=False, index=True)
    category = Column(String(64), nullable=False)
    classification = Column(String(64), nullable=False)
    traceback_excerpt = Column(Text, default="")
    suspected_file = Column(String(512), nullable=True)
    suspected_line = Column(Integer, nullable=True)
    related_requirement_ids = Column(JSON, default=list)
    hypotheses = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class RepairProposalModel(Base):
    """Database model for a repair proposal candidate."""
    __tablename__ = "repair_proposals"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    failure_ids = Column(JSON, default=list)
    target_artifact_path = Column(String(512), nullable=False)
    original_artifact_hash = Column(String(64), nullable=False)
    patched_artifact_hash = Column(String(64), nullable=True)
    original_content = Column(Text, nullable=True)
    patched_content = Column(Text, nullable=False)
    unified_diff = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    status = Column(String(64), default="proposed", nullable=False, index=True)
    risk_level = Column(String(64), default="low", nullable=False)
    generator_type = Column(String(64), default="deterministic_rule_engine")
    related_requirement_ids = Column(JSON, default=list)
    related_test_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)


class RepairAuditLogModel(Base):
    """Database model for immutable repair lifecycle audit trail."""
    __tablename__ = "repair_audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    repair_id = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    actor = Column(String(64), default="developer")
    from_status = Column(String(64), nullable=False)
    to_status = Column(String(64), nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
