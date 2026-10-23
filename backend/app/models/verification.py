"""
SQLAlchemy models for code artifacts, traceability links, and verification runs.
"""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from app.models.requirement import Base


class ProjectModel(Base):
    """Database model for an ingested code project."""
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    total_files = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    manifests = Column(JSON, default=list)
    test_frameworks = Column(JSON, default=list)
    test_commands = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    artifacts = relationship(
        "ArtifactModel",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ArtifactModel.relative_path",
    )
    links = relationship(
        "TraceabilityLinkModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    runs = relationship(
        "VerificationRunModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ArtifactModel(Base):
    """Database model for an ingested code artifact file."""
    __tablename__ = "code_artifacts"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False, index=True)
    relative_path = Column(String(512), nullable=False, index=True)
    file_type = Column(String(64), nullable=False)
    language = Column(String(64), nullable=False)
    sha256 = Column(String(64), nullable=False)
    size_bytes = Column(Integer, default=0)
    line_count = Column(Integer, default=0)
    symbols = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("ProjectModel", back_populates="artifacts")


class TraceabilityLinkModel(Base):
    """Database model for a requirement-to-code or requirement-to-test link."""
    __tablename__ = "traceability_links"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False, index=True)
    specification_id = Column(String(64), nullable=False, index=True)
    requirement_id = Column(String(32), nullable=False, index=True)
    artifact_path = Column(String(512), nullable=False)
    symbol_name = Column(String(255), nullable=True)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    link_type = Column(String(64), nullable=False)
    link_origin = Column(String(64), nullable=False)
    confidence = Column(Float, default=0.5)
    is_confirmed = Column(Boolean, default=False)
    rationale = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    project = relationship("ProjectModel", back_populates="links")


class VerificationRunModel(Base):
    """Database model for a completed or failed verification run."""
    __tablename__ = "verification_runs"

    id = Column(String(64), primary_key=True, index=True)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False, index=True)
    specification_id = Column(String(64), nullable=True, index=True)
    status = Column(String(64), nullable=False)
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    skipped_tests = Column(Integer, default=0)
    duration_ms = Column(Float, default=0.0)
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    exit_code = Column(Integer, nullable=True)
    static_analysis_passed = Column(Boolean, default=True)
    static_findings = Column(JSON, default=list)
    requirement_verdicts = Column(JSON, default=dict)
    docker_available = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("ProjectModel", back_populates="runs")
