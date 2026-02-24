"""Unit tests for rosforge.utils.fs."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.utils.fs import ensure_dir, safe_copy_dir, write_file


class TestEnsureDir:
    def test_creates_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c"
        result = ensure_dir(target)
        assert target.exists()
        assert result == target

    def test_idempotent(self, tmp_path: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        ensure_dir(target)  # should not raise
        assert target.exists()

    def test_accepts_string(self, tmp_path: Path) -> None:
        target = str(tmp_path / "str_path")
        ensure_dir(target)
        assert Path(target).exists()


class TestWriteFile:
    def test_writes_content(self, tmp_path: Path) -> None:
        path = tmp_path / "test.txt"
        write_file(path, "hello world")
        assert path.read_text() == "hello world"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "dir" / "file.txt"
        write_file(path, "content")
        assert path.exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "file.txt"
        write_file(path, "first")
        write_file(path, "second")
        assert path.read_text() == "second"

    def test_encoding_parameter(self, tmp_path: Path) -> None:
        path = tmp_path / "utf8.txt"
        content = "ROS2 — migrated"
        write_file(path, content, encoding="utf-8")
        assert path.read_text(encoding="utf-8") == content


class TestSafeCopyDir:
    def test_copies_files(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "file.txt").write_text("hello")
        dst = tmp_path / "dst"
        safe_copy_dir(src, dst)
        assert (dst / "file.txt").read_text() == "hello"

    def test_skips_git_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / ".git").mkdir()
        (src / ".git" / "HEAD").write_text("ref: refs/heads/main")
        (src / "file.txt").write_text("content")
        dst = tmp_path / "dst"
        safe_copy_dir(src, dst)
        assert not (dst / ".git").exists()
        assert (dst / "file.txt").exists()

    def test_skips_rosforge_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / ".rosforge").mkdir()
        (src / ".rosforge" / "data.json").write_text("{}")
        dst = tmp_path / "dst"
        safe_copy_dir(src, dst)
        assert not (dst / ".rosforge").exists()

    def test_dirs_exist_ok(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("a")
        dst = tmp_path / "dst"
        dst.mkdir()
        (dst / "b.txt").write_text("b")
        safe_copy_dir(src, dst)
        assert (dst / "a.txt").exists()
        assert (dst / "b.txt").exists()
