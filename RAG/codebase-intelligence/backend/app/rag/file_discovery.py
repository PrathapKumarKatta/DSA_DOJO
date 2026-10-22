import os
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, List, Set
from app.core.config import settings
from app.rag.secret_filter import is_sensitive_filename

IGNORED_DIRECTORIES: Set[str] = {
    ".git",
    ".github",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".idea",
    ".vscode",
    "coverage",
    ".coverage",
}

IGNORED_EXTENSIONS: Set[str] = {
    # Binaries and libraries
    ".pyc", ".pyo", ".pyd", ".exe", ".dll", ".so", ".dylib", ".o", ".a", ".class", ".jar", ".war",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    # Media and fonts
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp", ".tiff",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Data binaries / caches
    ".db", ".sqlite", ".sqlite3", ".pkl", ".parquet",
}

IGNORED_FILENAMES: Set[str] = {
    ".ds_store",
    "thumbs.db",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pipfile.lock",
    "cargo.lock",
}

LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".json": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "bash",
    ".bash": "bash",
    ".toml": "toml",
    ".txt": "text",
    ".html": "html",
    ".css": "css",
}


@dataclass
class DiscoveredFile:
    relative_path: str
    language: str
    content: str
    line_count: int
    size_bytes: int


def is_safe_zip_entry(filename: str, target_dir: Path) -> bool:
    """Detect zip slip or traversal attacks."""
    pure = PurePosixPath(filename)
    if pure.is_absolute() or ".." in pure.parts:
        return False
    resolved = (target_dir / filename).resolve()
    return resolved.is_relative_to(target_dir.resolve())


def extract_and_discover_files(zip_path: Path, extract_dir: Path) -> List[DiscoveredFile]:
    """
    Safely extract a ZIP archive and return filtered, valid source code files.
    Enforces upload size, extracted size, file count, and security constraints.
    """
    extract_dir.mkdir(parents=True, exist_ok=True)
    max_extracted_bytes = settings.MAX_EXTRACTED_SIZE_MB * 1024 * 1024
    max_single_file_bytes = settings.MAX_SINGLE_FILE_SIZE_KB * 1024
    max_files = settings.MAX_PROJECT_FILES

    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Uploaded file is not a valid ZIP archive.")

    total_uncompressed = 0
    file_count = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Pre-scan headers to prevent zip bombs, zip slips, symlinks
        for info in zf.infolist():
            # Check for symlink
            is_symlink = (info.external_attr >> 16) & 0o120000 == 0o120000
            if is_symlink:
                raise ValueError(f"ZIP archive contains forbidden symlink: {info.filename}")

            # Check safe path
            if not is_safe_zip_entry(info.filename, extract_dir):
                raise ValueError(f"Path traversal detected in ZIP entry: {info.filename}")

            # Check compression ratio for zip bomb defense
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > 100 and info.file_size > 10 * 1024 * 1024:
                    raise ValueError(f"Possible ZIP bomb detected in entry: {info.filename}")

            if not info.is_dir():
                total_uncompressed += info.file_size
                file_count += 1

                if total_uncompressed > max_extracted_bytes:
                    raise ValueError(
                        f"Extracted size exceeds maximum limit of {settings.MAX_EXTRACTED_SIZE_MB}MB."
                    )
                if file_count > max_files:
                    raise ValueError(
                        f"Project exceeds maximum allowed file count ({settings.MAX_PROJECT_FILES})."
                    )

        # Extract safely
        for info in zf.infolist():
            if not info.is_dir():
                zf.extract(info, extract_dir)

    # Walk extracted directory and filter files
    discovered: List[DiscoveredFile] = []

    # Check if archive has a single top-level root directory (e.g. repo-main/)
    top_items = list(extract_dir.iterdir())
    root_prefix = extract_dir
    if len(top_items) == 1 and top_items[0].is_dir():
        root_prefix = top_items[0]

    for root, dirs, files in os.walk(root_prefix):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d.lower() not in IGNORED_DIRECTORIES and not d.startswith(".")]

        for fname in files:
            file_path = Path(root) / fname
            rel_path = file_path.relative_to(root_prefix).as_posix()
            lower_name = fname.lower()
            ext = file_path.suffix.lower()

            # Ignore filter checks
            if lower_name in IGNORED_FILENAMES:
                continue
            if ext in IGNORED_EXTENSIONS:
                continue
            if is_sensitive_filename(rel_path):
                continue
            if file_path.stat().st_size > max_single_file_bytes:
                continue

            # Read content with UTF-8 fallback
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue

            # Skip pure binary or null-byte filled files
            if "\x00" in content:
                continue

            line_count = len(content.splitlines())
            language = LANGUAGE_MAP.get(ext, "text")

            discovered.append(
                DiscoveredFile(
                    relative_path=rel_path,
                    language=language,
                    content=content,
                    line_count=line_count,
                    size_bytes=len(content.encode("utf-8")),
                )
            )

    return discovered
