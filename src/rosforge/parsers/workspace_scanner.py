"""Detect and enumerate packages in a catkin workspace."""

from __future__ import annotations

from pathlib import Path


def is_catkin_workspace(path: Path) -> bool:
    """Check if *path* is a catkin workspace root.

    A directory is considered a catkin workspace when it has a ``src/``
    subdirectory that contains at least one ``package.xml`` file anywhere
    inside it.  As a secondary signal we also accept the presence of a
    ``.catkin_workspace`` marker file or a root ``CMakeLists.txt`` that
    contains the ``catkin_workspace()`` macro call.

    Args:
        path: Candidate workspace root directory.

    Returns:
        True if *path* looks like a catkin workspace, False otherwise.
    """
    if not path.is_dir():
        return False

    src_dir = path / "src"
    if not src_dir.is_dir():
        return False

    # Primary signal: src/ contains at least one package.xml
    for candidate in src_dir.rglob("package.xml"):
        if candidate.is_file():
            return True

    # Secondary signal: .catkin_workspace marker
    if (path / ".catkin_workspace").exists():
        return True

    # Secondary signal: root CMakeLists.txt with catkin_workspace() call
    root_cmake = path / "CMakeLists.txt"
    if root_cmake.is_file():
        try:
            text = root_cmake.read_text(encoding="utf-8", errors="replace")
            if "catkin_workspace()" in text:
                return True
        except Exception:
            pass

    return False


def discover_packages(workspace_path: Path) -> list[Path]:
    """Find all ROS1 packages inside a catkin workspace.

    Walks ``workspace_path/src/`` and collects every directory that
    directly contains a ``package.xml`` file.  Nested package directories
    (e.g. metapackage scenarios) are also returned — each ``package.xml``
    occurrence at any depth is treated as an independent package root.

    Args:
        workspace_path: Root of the catkin workspace (contains ``src/``).

    Returns:
        Sorted list of absolute package root paths.
    """
    src_dir = workspace_path.resolve() / "src"
    if not src_dir.is_dir():
        return []

    package_roots: list[Path] = []

    for package_xml in sorted(src_dir.rglob("package.xml")):
        if package_xml.is_file():
            package_roots.append(package_xml.parent.resolve())

    return sorted(package_roots)
