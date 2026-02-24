"""Unit tests for rosforge.knowledge.package_xml_rules."""

from __future__ import annotations

import pytest
from xml.etree import ElementTree as ET

from rosforge.knowledge.package_xml_rules import (
    ROS1_TO_ROS2_PACKAGES,
    transform_package_xml,
)
from rosforge.models.ir import Dependency, DependencyType, PackageMetadata


def _parse(xml_str: str) -> ET.Element:
    return ET.fromstring(xml_str)


def _make_metadata(**kwargs) -> PackageMetadata:
    defaults = {
        "name": "my_pkg",
        "version": "1.2.3",
        "description": "Test package",
        "maintainers": ["Alice"],
        "licenses": ["Apache-2.0"],
    }
    defaults.update(kwargs)
    return PackageMetadata(**defaults)


def _make_dep(name: str, dep_type: DependencyType = DependencyType.DEPEND) -> Dependency:
    return Dependency(name=name, dep_type=dep_type)


class TestRos1ToRos2Packages:
    def test_catkin_mapped_to_ament_cmake(self):
        assert ROS1_TO_ROS2_PACKAGES["catkin"] == "ament_cmake"

    def test_roscpp_mapped_to_rclcpp(self):
        assert ROS1_TO_ROS2_PACKAGES["roscpp"] == "rclcpp"

    def test_rospy_mapped_to_rclpy(self):
        assert ROS1_TO_ROS2_PACKAGES["rospy"] == "rclpy"

    def test_message_generation_mapped(self):
        assert ROS1_TO_ROS2_PACKAGES["message_generation"] == "rosidl_default_generators"

    def test_message_runtime_mapped(self):
        assert ROS1_TO_ROS2_PACKAGES["message_runtime"] == "rosidl_default_runtime"

    def test_tf_mapped_to_tf2_ros(self):
        assert ROS1_TO_ROS2_PACKAGES["tf"] == "tf2_ros"

    def test_dynamic_reconfigure_removed(self):
        assert ROS1_TO_ROS2_PACKAGES["dynamic_reconfigure"] == ""

    def test_std_msgs_unchanged(self):
        assert ROS1_TO_ROS2_PACKAGES["std_msgs"] == "std_msgs"


class TestTransformPackageXml:
    def test_format_attribute_is_3(self):
        xml = transform_package_xml(_make_metadata(), [])
        root = _parse(xml)
        assert root.get("format") == "3"

    def test_package_name_preserved(self):
        xml = transform_package_xml(_make_metadata(name="cool_pkg"), [])
        root = _parse(xml)
        assert root.findtext("name") == "cool_pkg"

    def test_version_preserved(self):
        xml = transform_package_xml(_make_metadata(version="2.3.4"), [])
        root = _parse(xml)
        assert root.findtext("version") == "2.3.4"

    def test_license_preserved(self):
        xml = transform_package_xml(_make_metadata(licenses=["MIT"]), [])
        root = _parse(xml)
        assert root.findtext("license") == "MIT"

    def test_buildtool_is_ament_cmake(self):
        xml = transform_package_xml(_make_metadata(), [])
        root = _parse(xml)
        buildtools = [el.text for el in root.findall("buildtool_depend")]
        assert "ament_cmake" in buildtools

    def test_catkin_buildtool_not_present(self):
        deps = [_make_dep("catkin", DependencyType.BUILDTOOL)]
        xml = transform_package_xml(_make_metadata(), deps)
        root = _parse(xml)
        buildtools = [el.text for el in root.findall("buildtool_depend")]
        assert "catkin" not in buildtools

    def test_roscpp_dep_remapped_to_rclcpp(self):
        deps = [_make_dep("roscpp", DependencyType.BUILD)]
        xml = transform_package_xml(_make_metadata(), deps)
        root = _parse(xml)
        build_deps = [el.text for el in root.findall("build_depend")]
        assert "rclcpp" in build_deps
        assert "roscpp" not in build_deps

    def test_dynamic_reconfigure_removed(self):
        deps = [_make_dep("dynamic_reconfigure", DependencyType.DEPEND)]
        xml = transform_package_xml(_make_metadata(), deps)
        assert "dynamic_reconfigure" not in xml

    def test_std_msgs_unchanged(self):
        deps = [_make_dep("std_msgs", DependencyType.DEPEND)]
        xml = transform_package_xml(_make_metadata(), deps)
        root = _parse(xml)
        all_deps = [el.text for el in root]
        assert "std_msgs" in all_deps

    def test_no_duplicate_deps(self):
        deps = [
            _make_dep("roscpp", DependencyType.BUILD),
            _make_dep("roscpp", DependencyType.BUILD),
        ]
        xml = transform_package_xml(_make_metadata(), deps)
        root = _parse(xml)
        build_deps = [el.text for el in root.findall("build_depend")]
        assert build_deps.count("rclcpp") == 1

    def test_export_build_type_ament_cmake(self):
        xml = transform_package_xml(_make_metadata(), [])
        root = _parse(xml)
        export = root.find("export")
        assert export is not None
        build_type = export.findtext("build_type")
        assert build_type == "ament_cmake"

    def test_xml_declaration_present(self):
        xml = transform_package_xml(_make_metadata(), [])
        assert xml.startswith('<?xml version="1.0"?>')

    def test_multiple_maintainers(self):
        xml = transform_package_xml(
            _make_metadata(maintainers=["Alice", "Bob"]), []
        )
        root = _parse(xml)
        maintainers = root.findall("maintainer")
        assert len(maintainers) == 2
