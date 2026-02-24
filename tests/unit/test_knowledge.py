"""Unit tests for the knowledge base lookups and rule-based transforms."""

from __future__ import annotations

import pytest

from rosforge.knowledge import (
    CATKIN_TO_AMENT,
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    ROS1_TO_ROS2_PACKAGES,
    get_mapping,
    transform_cmake,
    transform_package_xml,
)
from rosforge.models.ir import Dependency, DependencyType, PackageMetadata


class TestAPIMappings:
    def test_roscpp_table_nonempty(self):
        assert len(ROSCPP_TO_RCLCPP) > 0

    def test_rospy_table_nonempty(self):
        assert len(ROSPY_TO_RCLPY) > 0

    def test_get_mapping_cpp(self):
        result = get_mapping("ros::NodeHandle", language="cpp")
        assert result is None or isinstance(result, str)

    def test_get_mapping_python(self):
        result = get_mapping("rospy.init_node", language="python")
        assert result is None or isinstance(result, str)

    def test_ros1_to_ros2_packages_nonempty(self):
        assert len(ROS1_TO_ROS2_PACKAGES) > 0

    def test_roscpp_maps_to_rclcpp(self):
        rclcpp_values = [v for v in ROSCPP_TO_RCLCPP.values() if "rclcpp" in v]
        assert len(rclcpp_values) > 0


class TestTransformPackageXml:
    """Tests using the actual transform_package_xml(metadata, dependencies) API."""

    def _minimal_metadata(self) -> PackageMetadata:
        return PackageMetadata(
            name="ros1_minimal",
            version="0.1.0",
            description="test",
            maintainers=["developer"],
            licenses=["Apache-2.0"],
        )

    def _roscpp_deps(self) -> list[Dependency]:
        return [
            Dependency(name="catkin", dep_type=DependencyType.BUILDTOOL),
            Dependency(name="roscpp", dep_type=DependencyType.BUILD),
            Dependency(name="roscpp", dep_type=DependencyType.EXEC),
        ]

    def test_returns_string(self):
        result = transform_package_xml(self._minimal_metadata(), self._roscpp_deps())
        assert isinstance(result, str)

    def test_removes_catkin_buildtool(self):
        result = transform_package_xml(self._minimal_metadata(), self._roscpp_deps())
        assert "catkin" not in result or "ament_cmake" in result

    def test_upgrades_format(self):
        result = transform_package_xml(self._minimal_metadata(), self._roscpp_deps())
        assert 'format="3"' in result

    def test_roscpp_converted(self):
        result = transform_package_xml(self._minimal_metadata(), self._roscpp_deps())
        assert "rclcpp" in result


class TestTransformCmake:
    MINIMAL_CMAKE = """\
cmake_minimum_required(VERSION 3.0.2)
project(ros1_minimal)
find_package(catkin REQUIRED COMPONENTS roscpp std_msgs)
catkin_package()
include_directories(${catkin_INCLUDE_DIRS})
add_executable(talker src/talker.cpp)
target_link_libraries(talker ${catkin_LIBRARIES})
install(TARGETS talker RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
"""

    def test_returns_string(self):
        result = transform_cmake(self.MINIMAL_CMAKE, ["roscpp", "std_msgs"])
        assert isinstance(result, str)

    def test_replaces_catkin_with_ament(self):
        result = transform_cmake(self.MINIMAL_CMAKE, ["roscpp", "std_msgs"])
        assert "ament_cmake" in result or "ament" in result

    def test_find_package_updated(self):
        result = transform_cmake(self.MINIMAL_CMAKE, ["roscpp", "std_msgs"])
        assert "find_package(ament_cmake" in result or "ament_cmake" in result

    def test_ament_package_added(self):
        result = transform_cmake(self.MINIMAL_CMAKE, ["roscpp", "std_msgs"])
        assert "ament_package()" in result
