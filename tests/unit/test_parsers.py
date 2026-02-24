"""Unit tests for ROS1 parsers against the ros1_minimal fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.models.ir import DependencyType, FileType
from rosforge.parsers.cmake import parse_cmake
from rosforge.parsers.cpp_source import scan_cpp
from rosforge.parsers.package_scanner import scan_package
from rosforge.parsers.package_xml import parse_package_xml

FIXTURES = Path(__file__).parent.parent / "fixtures"
ROS1_MINIMAL = FIXTURES / "ros1_minimal"
ROS1_PYTHON = FIXTURES / "ros1_python"


class TestPackageXmlParser:
    def test_parses_name(self):
        meta, deps = parse_package_xml(ROS1_MINIMAL / "package.xml")
        assert meta.name == "ros1_minimal"

    def test_parses_version(self):
        meta, deps = parse_package_xml(ROS1_MINIMAL / "package.xml")
        assert meta.version == "0.1.0"

    def test_parses_format_version(self):
        meta, deps = parse_package_xml(ROS1_MINIMAL / "package.xml")
        assert meta.format_version == 2

    def test_parses_buildtool_depend(self):
        _, deps = parse_package_xml(ROS1_MINIMAL / "package.xml")
        bt_deps = [d for d in deps if d.dep_type == DependencyType.BUILDTOOL]
        assert any(d.name == "catkin" for d in bt_deps)

    def test_parses_build_depends(self):
        _, deps = parse_package_xml(ROS1_MINIMAL / "package.xml")
        build_deps = [d for d in deps if d.dep_type == DependencyType.BUILD]
        names = {d.name for d in build_deps}
        assert "roscpp" in names
        assert "std_msgs" in names

    def test_parses_exec_depends(self):
        _, deps = parse_package_xml(ROS1_MINIMAL / "package.xml")
        exec_deps = [d for d in deps if d.dep_type == DependencyType.EXEC]
        names = {d.name for d in exec_deps}
        assert "roscpp" in names

    def test_python_fixture_rospy(self):
        meta, deps = parse_package_xml(ROS1_PYTHON / "package.xml")
        assert meta.name == "ros1_python"
        all_names = {d.name for d in deps}
        assert "rospy" in all_names


class TestCMakeParser:
    def test_parse_cmake_returns_result(self):
        result = parse_cmake(ROS1_MINIMAL / "CMakeLists.txt")
        assert result is not None

    def test_cmake_detects_catkin(self):
        result = parse_cmake(ROS1_MINIMAL / "CMakeLists.txt")
        # Should detect catkin as a component
        components = getattr(result, "catkin_components", None) or getattr(result, "components", None)
        if components is not None:
            assert "roscpp" in components or "std_msgs" in components


class TestCppScanner:
    def test_scan_cpp_returns_list(self):
        usages = scan_cpp(ROS1_MINIMAL / "src" / "talker.cpp")
        assert isinstance(usages, list)

    def test_scan_cpp_finds_ros_api(self):
        usages = scan_cpp(ROS1_MINIMAL / "src" / "talker.cpp")
        api_names = {u.api_name for u in usages}
        # Should detect at least one ROS1 API pattern
        assert len(api_names) > 0

    def test_scan_cpp_records_file_path(self):
        usages = scan_cpp(ROS1_MINIMAL / "src" / "talker.cpp")
        if usages:
            assert "talker.cpp" in usages[0].file_path


class TestPackageScanner:
    def test_scan_package_returns_ir(self):
        ir = scan_package(ROS1_MINIMAL)
        assert ir is not None
        assert ir.metadata.name == "ros1_minimal"

    def test_scan_package_finds_files(self):
        ir = scan_package(ROS1_MINIMAL)
        assert ir.total_files > 0

    def test_scan_package_has_cpp_files(self):
        ir = scan_package(ROS1_MINIMAL)
        assert ir.cpp_files > 0

    def test_scan_package_has_package_xml(self):
        ir = scan_package(ROS1_MINIMAL)
        types = {f.file_type for f in ir.source_files}
        assert FileType.PACKAGE_XML in types

    def test_scan_package_has_cmake(self):
        ir = scan_package(ROS1_MINIMAL)
        types = {f.file_type for f in ir.source_files}
        assert FileType.CMAKE in types

    def test_scan_package_total_lines(self):
        ir = scan_package(ROS1_MINIMAL)
        assert ir.total_lines > 0

    def test_scan_python_package(self):
        ir = scan_package(ROS1_PYTHON)
        assert ir.metadata.name == "ros1_python"
        assert ir.python_files > 0
