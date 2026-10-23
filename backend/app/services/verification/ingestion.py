"""
Code Artifact Ingestion Service.
Safely ingests, validates, unpacks, and fingerprints source code archives.
Enforces strict security boundaries: rejects path traversal, symlinks, and zip bombs,
filters secrets and dependencies, computes SHA-256 fingerprints, and extracts symbols.
"""

import ast
import hashlib
import io
import os
import re
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.verification import (
    ArtifactMetadata,
    FileType,
    ProjectIngestionReport,
)

settings = get_settings()

IGNORED_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".egg-info",
    ".coverage",
    ".mypy_cache",
    ".ruff_cache",
}

SECRET_PATTERNS = [
    re.compile(r"^\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"^id_rsa(\..+)?$", re.IGNORECASE),
    re.compile(r"^.*\.(pem|key|pfx|p12|pkcs12)$", re.IGNORECASE),
    re.compile(r"^(credentials|secrets|passwords)\.(json|yaml|yml|txt)$", re.IGNORECASE),
]

ALLOWED_EXTENSIONS: Set[str] = {
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".cfg",
    ".ini",
    ".sh",
    ".sql",
}

PROJECTS_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "projects"


class IngestionSecurityError(Exception):
    """Raised when an uploaded archive breaches safety policies."""
    pass


class CodeArtifactIngestionService:
    """
    Safely unpacks and inventories source code projects without executing untrusted code.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or PROJECTS_DATA_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def ingest_zip_archive(
        self,
        archive_bytes: bytes,
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> ProjectIngestionReport:
        """
        Validates, sanitizes, and extracts a ZIP archive into a dedicated project directory.
        """
        # 1. Archive-level size check
        if len(archive_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise IngestionSecurityError(
                f"Archive size ({len(archive_bytes)} bytes) exceeds maximum limit "
                f"({settings.MAX_UPLOAD_SIZE_BYTES} bytes)."
            )

        proj_id = project_id or f"prj-{uuid.uuid4().hex[:12]}"
        proj_name = project_name or f"Project-{proj_id[-6:]}"
        dest_dir = self.storage_dir / proj_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        warnings: List[str] = []
        artifacts: List[ArtifactMetadata] = []
        total_uncompressed_bytes = 0
        total_files = 0
        artifact_counter = 1

        try:
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                infolist = zf.infolist()

                # File count limit check
                if len(infolist) > settings.MAX_UPLOAD_FILE_COUNT:
                    raise IngestionSecurityError(
                        f"Archive contains {len(infolist)} entries, exceeding maximum limit "
                        f"({settings.MAX_UPLOAD_FILE_COUNT} files)."
                    )

                # Process each entry safely
                for entry in infolist:
                    if entry.is_dir():
                        continue

                    # Uncompressed size defense (Zip bomb)
                    total_uncompressed_bytes += entry.file_size
                    if total_uncompressed_bytes > 50 * 1024 * 1024:
                        raise IngestionSecurityError(
                            "Uncompressed archive volume exceeds 50MB safety limit (zip bomb protection)."
                        )

                    # Validate path traversal and normalize
                    raw_filename = entry.filename.replace("\\", "/")
                    norm_path = os.path.normpath(raw_filename).replace("\\", "/")

                    if (
                        norm_path.startswith("..")
                        or norm_path.startswith("/")
                        or re.match(r"^[a-zA-Z]:", norm_path)
                    ):
                        raise IngestionSecurityError(
                            f"Unsafe path traversal detected in archive entry: '{entry.filename}'"
                        )

                    # Symlink / special entry rejection
                    # UNIX symlinks have attribute & 0o120000 == 0o120000
                    if (entry.external_attr >> 16) & 0o120000 == 0o120000:
                        warnings.append(f"Skipped symlink entry: {norm_path}")
                        continue

                    # Filter ignored directories
                    path_parts = norm_path.split("/")
                    if any(part in IGNORED_DIRS for part in path_parts):
                        continue

                    filename_only = path_parts[-1]

                    # Filter secrets and credentials
                    if any(p.match(filename_only) for p in SECRET_PATTERNS):
                        warnings.append(
                            f"Excluded potentially sensitive file matching security filter: '{norm_path}'"
                        )
                        continue

                    # Check extension
                    _, ext = os.path.splitext(filename_only)
                    ext = ext.lower()
                    if ext and ext not in ALLOWED_EXTENSIONS:
                        warnings.append(
                            f"Skipped unsupported file type '{ext}': '{norm_path}'"
                        )
                        continue

                    # Extract file content safely into memory
                    file_bytes = zf.read(entry)
                    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

                    # Write sanitized file to target workspace
                    target_file_path = dest_dir / norm_path
                    target_file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_file_path, "wb") as f_out:
                        f_out.write(file_bytes)

                    # Classify file type and language
                    file_type, language = self._classify_file(norm_path, ext)
                    line_count = len(file_bytes.splitlines())

                    # Extract symbols from Python code
                    symbols = []
                    if language == "python":
                        symbols = self._extract_python_symbols(file_bytes, norm_path, warnings)

                    art_id = f"ART-{artifact_counter:03d}"
                    artifact_counter += 1

                    artifacts.append(
                        ArtifactMetadata(
                            id=art_id,
                            project_id=proj_id,
                            relative_path=norm_path,
                            file_type=file_type,
                            language=language,
                            sha256=sha256_hash,
                            size_bytes=len(file_bytes),
                            line_count=line_count,
                            symbols=symbols,
                            created_at=datetime.utcnow().isoformat() + "Z",
                        )
                    )
                    total_files += 1

        except zipfile.BadZipFile:
            raise IngestionSecurityError("The provided payload is not a valid ZIP archive.")

        # Identify recognized manifests and test commands
        manifests, test_frameworks, test_commands = self._detect_environment(artifacts)

        now_iso = datetime.utcnow().isoformat() + "Z"
        return ProjectIngestionReport(
            project_id=proj_id,
            name=proj_name,
            total_files=total_files,
            total_size_bytes=total_uncompressed_bytes,
            detected_manifests=manifests,
            detected_test_frameworks=test_frameworks,
            available_test_commands=test_commands,
            ingested_artifacts=artifacts,
            warnings=warnings,
            ingested_at=now_iso,
        )

    def ingest_files_dictionary(
        self,
        files: Dict[str, str],
        project_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> ProjectIngestionReport:
        """
        Ingests a dictionary of {relative_path: content_string} directly.
        Useful for programmatic API testing and presets.
        """
        proj_id = project_id or f"prj-{uuid.uuid4().hex[:12]}"
        proj_name = project_name or f"Project-{proj_id[-6:]}"
        dest_dir = self.storage_dir / proj_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        warnings: List[str] = []
        artifacts: List[ArtifactMetadata] = []
        total_bytes = 0
        artifact_counter = 1

        for raw_path, content in files.items():
            norm_path = os.path.normpath(raw_path.replace("\\", "/")).replace("\\", "/")
            if norm_path.startswith("..") or norm_path.startswith("/"):
                warnings.append(f"Skipped unsafe path: '{raw_path}'")
                continue

            file_bytes = content.encode("utf-8")
            total_bytes += len(file_bytes)
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()

            target_file_path = dest_dir / norm_path
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file_path, "wb") as f_out:
                f_out.write(file_bytes)

            _, ext = os.path.splitext(norm_path)
            file_type, language = self._classify_file(norm_path, ext.lower())
            symbols = []
            if language == "python":
                symbols = self._extract_python_symbols(file_bytes, norm_path, warnings)

            art_id = f"ART-{artifact_counter:03d}"
            artifact_counter += 1

            artifacts.append(
                ArtifactMetadata(
                    id=art_id,
                    project_id=proj_id,
                    relative_path=norm_path,
                    file_type=file_type,
                    language=language,
                    sha256=sha256_hash,
                    size_bytes=len(file_bytes),
                    line_count=len(content.splitlines()),
                    symbols=symbols,
                    created_at=datetime.utcnow().isoformat() + "Z",
                )
            )

        manifests, test_frameworks, test_commands = self._detect_environment(artifacts)
        now_iso = datetime.utcnow().isoformat() + "Z"

        return ProjectIngestionReport(
            project_id=proj_id,
            name=proj_name,
            total_files=len(artifacts),
            total_size_bytes=total_bytes,
            detected_manifests=manifests,
            detected_test_frameworks=test_frameworks,
            available_test_commands=test_commands,
            ingested_artifacts=artifacts,
            warnings=warnings,
            ingested_at=now_iso,
        )

    def _classify_file(self, rel_path: str, ext: str) -> Tuple[FileType, str]:
        """Classify file type and programming language."""
        path_lower = rel_path.lower()
        filename = path_lower.split("/")[-1]

        # Determine language
        lang_map = {
            ".py": "python",
            ".json": "json",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".txt": "text",
            ".cfg": "config",
            ".ini": "config",
            ".sh": "shell",
            ".sql": "sql",
        }
        language = lang_map.get(ext, "unknown")

        # Determine file type
        if filename in {"requirements.txt", "pyproject.toml", "setup.py", "package.json", "pom.xml"}:
            return FileType.MANIFEST, language
        if filename in {"pytest.ini", "setup.cfg", "tox.ini", "dockerfile", ".gitignore"}:
            return FileType.CONFIG, language
        if ext in {".md", ".rst"}:
            return FileType.DOCUMENTATION, language

        # Check for test files
        if (
            filename.startswith("test_")
            or filename.endswith("_test.py")
            or "/tests/" in f"/{path_lower}/"
            or "/test/" in f"/{path_lower}/"
        ):
            return FileType.TEST_FILE, language

        if ext == ".py":
            return FileType.SOURCE_FILE, language

        return FileType.OTHER, language

    def _extract_python_symbols(
        self, file_bytes: bytes, rel_path: str, warnings: List[str]
    ) -> List[str]:
        """Safely extracts top-level and class-level functions and classes via AST."""
        symbols: List[str] = []
        try:
            tree = ast.parse(file_bytes.decode("utf-8", errors="replace"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols.append(f"class:{node.name}")
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            symbols.append(f"method:{node.name}.{item.name}")
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only add top-level if not already captured under a class
                    symbols.append(f"def:{node.name}")
        except SyntaxError as e:
            warnings.append(f"Syntax error while parsing symbols from '{rel_path}': line {e.lineno}")
        except Exception as e:
            warnings.append(f"Could not parse AST symbols from '{rel_path}': {e}")
        return list(dict.fromkeys(symbols))

    def _detect_environment(
        self, artifacts: List[ArtifactMetadata]
    ) -> Tuple[List[str], List[str], List[str]]:
        """Identifies recognized manifests, test frameworks, and safe test execution commands."""
        manifests: List[str] = []
        test_frameworks: List[str] = []
        test_commands: List[str] = []

        artifact_paths = {a.relative_path.lower() for a in artifacts}

        for path in artifact_paths:
            fname = path.split("/")[-1]
            if fname in {"requirements.txt", "pyproject.toml", "setup.py", "package.json"}:
                manifests.append(fname)

        # Detect Python pytest
        has_python_tests = any(a.file_type == FileType.TEST_FILE for a in artifacts)
        has_python_sources = any(a.language == "python" for a in artifacts)

        if has_python_tests or has_python_sources:
            test_frameworks.append("pytest (Python)")
            test_commands.append("pytest -v")

        return sorted(list(set(manifests))), test_frameworks, test_commands
