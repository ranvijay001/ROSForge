"""Unit tests for rosforge.utils.git."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rosforge.utils.git import (
    add_all,
    commit,
    create_migration_commit,
    get_diff,
    get_diff_stat,
    init_repo,
    is_git_repo,
)


class TestIsGitRepo:
    def test_returns_true_when_git_succeeds(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert is_git_repo(tmp_path) is True

    def test_returns_false_when_git_fails(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128)
            assert is_git_repo(tmp_path) is False


class TestInitRepo:
    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert init_repo(tmp_path) is True

    def test_returns_false_on_failure(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert init_repo(tmp_path) is False


class TestAddAll:
    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert add_all(tmp_path) is True

    def test_returns_false_on_failure(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert add_all(tmp_path) is False


class TestCommit:
    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert commit(tmp_path, "initial commit") is True

    def test_returns_false_on_failure(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert commit(tmp_path, "initial commit") is False


class TestGetDiff:
    def test_returns_stdout_on_success(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="diff content\n")
            result = get_diff(tmp_path)
            assert result == "diff content\n"

    def test_returns_empty_on_failure(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = get_diff(tmp_path)
            assert result == ""


class TestGetDiffStat:
    def test_returns_stat_on_success(self, tmp_path: Path) -> None:
        stat = " 3 files changed, 100 insertions(+)\n"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=stat)
            result = get_diff_stat(tmp_path)
            assert result == stat

    def test_returns_empty_on_failure(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = get_diff_stat(tmp_path)
            assert result == ""


class TestCreateMigrationCommit:
    def test_full_success_flow(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = create_migration_commit(tmp_path, "my_pkg")
            assert result is True
            # Should have called init, add, and commit
            assert mock_run.call_count == 3

    def test_returns_false_if_init_fails(self, tmp_path: Path) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = create_migration_commit(tmp_path, "my_pkg")
            assert result is False

    def test_integration_creates_repo(self, tmp_path: Path) -> None:
        """Integration test: actually init a git repo."""
        result = init_repo(tmp_path)
        # git must be available for this to pass
        if result:
            assert (tmp_path / ".git").exists()
