import io
import zipfile
from pathlib import Path
import pytest
from app.rag.file_discovery import extract_and_discover_files


def test_reject_zip_slip(tmp_path: Path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0::/root:/bin/bash")
    zip_bytes.seek(0)

    zip_file = tmp_path / "slip.zip"
    zip_file.write_bytes(zip_bytes.getvalue())

    dest_dir = tmp_path / "extracted_slip"
    with pytest.raises(ValueError, match="Path traversal detected"):
        extract_and_discover_files(zip_file, dest_dir)


def test_reject_absolute_path_zip(tmp_path: Path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("/root/malicious.py", "print('hacked')")
    zip_bytes.seek(0)

    zip_file = tmp_path / "abs.zip"
    zip_file.write_bytes(zip_bytes.getvalue())

    dest_dir = tmp_path / "extracted_abs"
    with pytest.raises(ValueError, match="Path traversal detected"):
        extract_and_discover_files(zip_file, dest_dir)


def test_reject_invalid_zip(tmp_path: Path):
    fake_zip = tmp_path / "corrupt.zip"
    fake_zip.write_bytes(b"not a real zip file header content")

    dest_dir = tmp_path / "extracted_fake"
    with pytest.raises(ValueError, match="not a valid ZIP archive"):
        extract_and_discover_files(fake_zip, dest_dir)


def test_filter_ignored_dirs_and_files(tmp_path: Path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("project/main.py", "def main(): pass")
        zf.writestr("project/.git/config", "secret git config")
        zf.writestr("project/node_modules/package/index.js", "ignored js")
        zf.writestr("project/venv/bin/activate", "ignored venv")
        zf.writestr("project/__pycache__/main.cpython-311.pyc", "binary pyc")
        zf.writestr("project/.env", "SECRET_KEY=12345")
        zf.writestr("project/image.png", b"\x89PNG\r\n\x1a\n")

    zip_file = tmp_path / "valid.zip"
    zip_file.write_bytes(zip_bytes.getvalue())

    dest_dir = tmp_path / "extracted_valid"
    discovered = extract_and_discover_files(zip_file, dest_dir)

    paths = [f.relative_path for f in discovered]
    assert "main.py" in paths
    assert not any(".git" in p for p in paths)
    assert not any("node_modules" in p for p in paths)
    assert not any("venv" in p for p in paths)
    assert not any(".env" in p for p in paths)
    assert not any("image.png" in p for p in paths)
