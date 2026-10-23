"""
Unit tests for Code Artifact Ingestion Service.
Tests archive validation, path traversal rejection, secret exclusion,
SHA-256 hashing, symbol extraction, and manifest detection.
"""

import io
import zipfile
import pytest
from app.schemas.verification import FileType
from app.services.verification.ingestion import (
    CodeArtifactIngestionService,
    IngestionSecurityError,
)


def create_test_zip(file_dict: dict) -> bytes:
    """Helper creating an in-memory ZIP archive from a dict of {path: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in file_dict.items():
            zf.writestr(path, content)
    return buf.getvalue()


def test_safe_archive_ingestion(tmp_path):
    """Verify standard valid archive is extracted, fingerprinted, and inventoried."""
    svc = CodeArtifactIngestionService(storage_dir=tmp_path)

    files = {
        "src/calculator.py": "def add(a: int, b: int) -> int:\n    return a + b\n",
        "tests/test_calculator.py": "def test_add():\n    assert add(1, 2) == 3\n",
        "requirements.txt": "pytest>=8.0.0\n",
        "README.md": "# Calculator Project\n",
    }
    archive_bytes = create_test_zip(files)

    report = svc.ingest_zip_archive(archive_bytes, project_name="Test Calculator")

    assert report.total_files == 4
    assert report.name == "Test Calculator"
    assert "requirements.txt" in report.detected_manifests
    assert any("pytest" in tf for tf in report.detected_test_frameworks)

    # Check artifacts
    art_map = {a.relative_path: a for a in report.ingested_artifacts}
    assert "src/calculator.py" in art_map
    assert art_map["src/calculator.py"].file_type == FileType.SOURCE_FILE
    assert "def:add" in art_map["src/calculator.py"].symbols
    assert len(art_map["src/calculator.py"].sha256) == 64

    assert "tests/test_calculator.py" in art_map
    assert art_map["tests/test_calculator.py"].file_type == FileType.TEST_FILE
    assert "def:test_add" in art_map["tests/test_calculator.py"].symbols


def test_reject_path_traversal(tmp_path):
    """Verify archive entries attempting path traversal are rejected with security error."""
    svc = CodeArtifactIngestionService(storage_dir=tmp_path)

    malicious_files = {
        "src/app.py": "print('ok')",
        "../../etc/passwd": "root:x:0:0::/root:/bin/bash",
    }
    archive_bytes = create_test_zip(malicious_files)

    with pytest.raises(IngestionSecurityError) as exc_info:
        svc.ingest_zip_archive(archive_bytes)

    assert "path traversal" in str(exc_info.value).lower()


def test_secrets_and_ignored_directories_filtered(tmp_path):
    """Verify .env secrets and node_modules / venv directories are filtered."""
    svc = CodeArtifactIngestionService(storage_dir=tmp_path)

    files = {
        "src/main.py": "def run(): pass",
        ".env": "DATABASE_PASSWORD=supersecret",
        ".env.local": "SECRET_KEY=12345",
        "secrets.json": "{\"apiKey\": \"secret\"}",
        "server.key": "-----BEGIN PRIVATE KEY-----",
        "node_modules/pkg/index.js": "module.exports = {}",
        ".venv/lib/site.py": "print('venv')",
        "__pycache__/mod.cpython-311.pyc": "bytecode",
    }
    archive_bytes = create_test_zip(files)

    report = svc.ingest_zip_archive(archive_bytes)

    # Only src/main.py should be ingested
    assert report.total_files == 1
    assert report.ingested_artifacts[0].relative_path == "src/main.py"
    # Secrets should have produced warnings
    assert any("sensitive" in w.lower() for w in report.warnings)


def test_file_count_limit_rejection(tmp_path, monkeypatch):
    """Verify archive exceeding file count limit is safely rejected."""
    from app.core import config
    settings = config.get_settings()
    monkeypatch.setattr(settings, "MAX_UPLOAD_FILE_COUNT", 5)

    svc = CodeArtifactIngestionService(storage_dir=tmp_path)

    too_many_files = {f"file_{i}.py": f"x = {i}" for i in range(10)}
    archive_bytes = create_test_zip(too_many_files)

    with pytest.raises(IngestionSecurityError) as exc_info:
        svc.ingest_zip_archive(archive_bytes)

    assert "maximum limit" in str(exc_info.value).lower()
