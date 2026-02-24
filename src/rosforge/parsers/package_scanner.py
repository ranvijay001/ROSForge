"""Walk a ROS1 package directory and assemble a PackageIR."""

from __future__ import annotations

import logging
from pathlib import Path

from rosforge.models.ir import FileType, PackageIR, PackageMetadata, ROSAPIUsage, SourceFile
from rosforge.parsers.cmake import parse_cmake
from rosforge.parsers.cpp_source import scan_cpp
from rosforge.parsers.launch_xml import parse_launch_xml
from rosforge.parsers.msg_srv import parse_msg_srv
from rosforge.parsers.package_xml import parse_package_xml
from rosforge.parsers.python_source import scan_python

logger = logging.getLogger(__name__)

# Directories to skip during traversal
_SKIP_DIRS = {".git", ".svn", "__pycache__", "build", "devel", ".catkin_tools"}


def _classify(path: Path) -> FileType:
    """Classify a file into a FileType based on its name and extension."""
    name = path.name
    suffix = path.suffix.lower()

    if name == "CMakeLists.txt":
        return FileType.CMAKE
    if name == "package.xml":
        return FileType.PACKAGE_XML
    if suffix in (".cpp", ".cc", ".cxx"):
        return FileType.CPP
    if suffix in (".hpp", ".h", ".hh", ".hxx"):
        return FileType.HPP
    if suffix == ".py":
        return FileType.PYTHON
    if suffix == ".launch" or (suffix == ".xml" and "launch" in name.lower()):
        return FileType.LAUNCH_XML
    if suffix == ".msg":
        return FileType.MSG
    if suffix == ".srv":
        return FileType.SRV
    if suffix == ".action":
        return FileType.ACTION
    return FileType.OTHER


def _read_content(path: Path) -> tuple[str, int]:
    """Read file content and count lines. Returns (content, line_count)."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return content, content.count("\n") + (1 if content else 0)
    except Exception as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return "", 0


def scan_package(path: Path) -> PackageIR:
    """Walk a ROS1 package directory and assemble a PackageIR.

    Args:
        path: Root directory of the ROS1 package (must contain package.xml).

    Returns:
        Populated PackageIR instance.
    """
    path = path.resolve()
    ir = PackageIR(source_path=path)

    all_api_usages: list[ROSAPIUsage] = []

    for file_path in sorted(path.rglob("*")):
        # Skip directories and blacklisted dir names
        if file_path.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in file_path.parts):
            continue

        file_type = _classify(file_path)
        if file_type == FileType.OTHER:
            continue

        relative = str(file_path.relative_to(path))
        content, line_count = _read_content(file_path)

        source_file = SourceFile(
            relative_path=relative,
            file_type=file_type,
            content=content,
            line_count=line_count,
        )

        # --- Per-type parsing ---
        if file_type == FileType.PACKAGE_XML:
            try:
                metadata, deps = parse_package_xml(file_path)
                ir.metadata = metadata
                ir.dependencies = deps
            except Exception as exc:
                logger.warning("package_xml parse error for %s: %s", file_path, exc)

        elif file_type == FileType.CMAKE:
            try:
                parse_cmake(file_path)  # result stored for future use; not in IR yet
            except Exception as exc:
                logger.warning("cmake parse error for %s: %s", file_path, exc)

        elif file_type in (FileType.CPP, FileType.HPP):
            try:
                usages = scan_cpp(file_path)
                source_file.api_usages = usages
                all_api_usages.extend(usages)
            except Exception as exc:
                logger.warning("cpp scan error for %s: %s", file_path, exc)

        elif file_type == FileType.PYTHON:
            try:
                usages = scan_python(file_path)
                source_file.api_usages = usages
                all_api_usages.extend(usages)
            except Exception as exc:
                logger.warning("python scan error for %s: %s", file_path, exc)

        elif file_type == FileType.LAUNCH_XML:
            try:
                parse_launch_xml(file_path)
            except Exception as exc:
                logger.warning("launch_xml parse error for %s: %s", file_path, exc)

        elif file_type in (FileType.MSG, FileType.SRV, FileType.ACTION):
            try:
                parse_msg_srv(file_path)
            except Exception as exc:
                logger.warning("msg/srv parse error for %s: %s", file_path, exc)

        ir.source_files.append(source_file)

    # Aggregate API usages
    ir.api_usages = all_api_usages

    # Compute summary stats
    ir.total_files = len(ir.source_files)
    ir.total_lines = sum(f.line_count for f in ir.source_files)
    ir.cpp_files = sum(1 for f in ir.source_files if f.file_type in (FileType.CPP, FileType.HPP))
    ir.python_files = sum(1 for f in ir.source_files if f.file_type == FileType.PYTHON)
    ir.launch_files = sum(1 for f in ir.source_files if f.file_type == FileType.LAUNCH_XML)
    ir.msg_srv_files = sum(
        1 for f in ir.source_files if f.file_type in (FileType.MSG, FileType.SRV, FileType.ACTION)
    )

    # Fallback metadata if package.xml was missing
    if not ir.metadata.name:
        ir.metadata = PackageMetadata(name=path.name)
        logger.warning("No package.xml found in %s; using directory name as package name", path)

    return ir
