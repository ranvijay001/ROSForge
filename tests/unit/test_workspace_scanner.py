"""Unit tests for workspace_scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.parsers.workspace_scanner import discover_packages, is_catkin_workspace

# Path to the bundled catkin workspace fixture
FIXTURE_WS = Path(__file__).parent.parent / "fixtures" / "catkin_ws"


class TestIsCatkinWorkspace:
    def test_is_catkin_workspace_true(self) -> None:
        """The fixture directory is detected as a catkin workspace."""
        assert is_catkin_workspace(FIXTURE_WS) is True

    def test_is_catkin_workspace_false_single_package(self, tmp_path: Path) -> None:
        """A bare package directory (no src/) is not a workspace."""
        pkg = tmp_path / "my_package"
        pkg.mkdir()
        (pkg / "package.xml").write_text("<package/>", encoding="utf-8")
        assert is_catkin_workspace(pkg) is False

    def test_is_catkin_workspace_false_no_src(self, tmp_path: Path) -> None:
        """Directory without src/ is not a workspace."""
        assert is_catkin_workspace(tmp_path) is False

    def test_is_catkin_workspace_false_empty_src(self, tmp_path: Path) -> None:
        """Directory with empty src/ (no packages) is not a workspace."""
        (tmp_path / "src").mkdir()
        assert is_catkin_workspace(tmp_path) is False

    def test_is_catkin_workspace_via_marker_file(self, tmp_path: Path) -> None:
        """Directory is detected as workspace via .catkin_workspace marker."""
        (tmp_path / "src").mkdir()
        (tmp_path / ".catkin_workspace").write_text("", encoding="utf-8")
        assert is_catkin_workspace(tmp_path) is True

    def test_is_catkin_workspace_via_cmake_macro(self, tmp_path: Path) -> None:
        """Directory is detected as workspace via CMakeLists.txt catkin_workspace() macro."""
        (tmp_path / "src").mkdir()
        (tmp_path / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.0.2)\ncatkin_workspace()\n",
            encoding="utf-8",
        )
        assert is_catkin_workspace(tmp_path) is True

    def test_is_catkin_workspace_nonexistent(self, tmp_path: Path) -> None:
        """Non-existent path returns False."""
        assert is_catkin_workspace(tmp_path / "ghost") is False


class TestDiscoverPackages:
    def test_discover_packages(self) -> None:
        """Fixture workspace should yield pkg_a and pkg_b."""
        packages = discover_packages(FIXTURE_WS)
        names = [p.name for p in packages]
        assert "pkg_a" in names
        assert "pkg_b" in names

    def test_discover_packages_count(self) -> None:
        """Fixture workspace should yield exactly 2 packages."""
        packages = discover_packages(FIXTURE_WS)
        assert len(packages) == 2

    def test_discover_packages_sorted(self) -> None:
        """Returned list must be sorted."""
        packages = discover_packages(FIXTURE_WS)
        names = [p.name for p in packages]
        assert names == sorted(names)

    def test_discover_packages_returns_absolute_paths(self) -> None:
        """All returned paths must be absolute."""
        for pkg in discover_packages(FIXTURE_WS):
            assert pkg.is_absolute()

    def test_discover_nested_packages(self, tmp_path: Path) -> None:
        """Metapackage scenario: nested packages are all discovered."""
        # workspace/src/meta/child_a/package.xml
        #                    child_b/package.xml
        src = tmp_path / "src"
        meta = src / "meta"
        child_a = meta / "child_a"
        child_b = meta / "child_b"
        child_a.mkdir(parents=True)
        child_b.mkdir(parents=True)
        (child_a / "package.xml").write_text("<package/>", encoding="utf-8")
        (child_b / "package.xml").write_text("<package/>", encoding="utf-8")

        packages = discover_packages(tmp_path)
        names = {p.name for p in packages}
        assert names == {"child_a", "child_b"}

    def test_empty_workspace(self, tmp_path: Path) -> None:
        """A workspace with an empty src/ returns an empty list."""
        (tmp_path / "src").mkdir()
        packages = discover_packages(tmp_path)
        assert packages == []

    def test_no_src_directory(self, tmp_path: Path) -> None:
        """A path with no src/ returns an empty list."""
        packages = discover_packages(tmp_path)
        assert packages == []
