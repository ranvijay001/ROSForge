"""Filesystem utility helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

_SKIP_DIRS = {".git", ".rosforge"}


def safe_copy_dir(src: Path | str, dst: Path | str) -> None:
    """Recursively copy a directory, skipping .git and .rosforge entries.

    Args:
        src: Source directory path.
        dst: Destination directory path. Created if it does not exist.
    """
    src = Path(src)
    dst = Path(dst)

    def _ignore(directory: str, contents: list[str]) -> set[str]:
        return {name for name in contents if name in _SKIP_DIRS}

    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def ensure_dir(path: Path | str) -> Path:
    """Create directory (and parents) if it does not exist.

    Args:
        path: Directory path to create.

    Returns:
        The resolved Path object.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_file(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Write text content to a file, creating parent directories as needed.

    Args:
        path: Destination file path.
        content: Text content to write.
        encoding: File encoding (default: utf-8).
    """
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(content, encoding=encoding)
