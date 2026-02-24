"""Git utility helpers for ROSForge."""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(path: Path | str) -> bool:
    """Return True if *path* is inside a git repository.

    Args:
        path: Directory to check.

    Returns:
        True if a .git directory exists at or above *path*.
    """
    path = Path(path)
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def init_repo(path: Path | str) -> bool:
    """Initialise a new git repository at *path*.

    Args:
        path: Directory in which to run ``git init``.

    Returns:
        True on success, False if the command fails.
    """
    path = Path(path)
    result = subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def add_all(path: Path | str) -> bool:
    """Stage all files in *path* (``git add -A``).

    Args:
        path: Working tree root.

    Returns:
        True on success.
    """
    result = subprocess.run(
        ["git", "add", "-A"],
        cwd=Path(path),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def commit(path: Path | str, message: str) -> bool:
    """Create an initial commit in the repository at *path*.

    Args:
        path: Working tree root.
        message: Commit message.

    Returns:
        True on success.
    """
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=Path(path),
        capture_output=True,
        text=True,
        env=_minimal_git_env(),
    )
    return result.returncode == 0


def get_diff(path: Path | str, ref: str = "HEAD") -> str:
    """Return the unified diff of working-tree changes vs *ref*.

    Args:
        path: Working tree root.
        ref: Git reference to diff against (default: HEAD).

    Returns:
        Unified diff string, or empty string if nothing changed or git fails.
    """
    result = subprocess.run(
        ["git", "diff", ref],
        cwd=Path(path),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    return ""


def get_diff_stat(path: Path | str, ref: str = "HEAD") -> str:
    """Return ``git diff --stat`` output vs *ref*.

    Args:
        path: Working tree root.
        ref: Git reference to diff against (default: HEAD).

    Returns:
        Stat string or empty string on failure.
    """
    result = subprocess.run(
        ["git", "diff", "--stat", ref],
        cwd=Path(path),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    return ""


def create_migration_commit(output_path: Path | str, package_name: str) -> bool:
    """Initialise a git repo, stage all files, and create an initial commit.

    Convenience wrapper used by the pipeline after copying the output tree.

    Args:
        output_path: The migrated package directory.
        package_name: Package name for the commit message.

    Returns:
        True if the commit was created successfully.
    """
    output_path = Path(output_path)
    if not init_repo(output_path):
        return False
    if not add_all(output_path):
        return False
    return commit(
        output_path,
        f"chore: initial ROS2 migration of {package_name} via ROSForge",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _minimal_git_env() -> dict[str, str]:
    """Return a minimal environment that git needs for committing."""
    import os

    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "ROSForge")
    env.setdefault("GIT_AUTHOR_EMAIL", "rosforge@local")
    env.setdefault("GIT_COMMITTER_NAME", "ROSForge")
    env.setdefault("GIT_COMMITTER_EMAIL", "rosforge@local")
    return env
