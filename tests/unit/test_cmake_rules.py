"""Unit tests for rosforge.knowledge.cmake_rules."""

from __future__ import annotations

import pytest

from rosforge.knowledge.cmake_rules import CATKIN_TO_AMENT, transform_cmake


class TestCatkinToAment:
    def test_catkin_package_mapped(self):
        assert CATKIN_TO_AMENT["catkin_package"] == "ament_package"

    def test_add_message_files_mapped(self):
        assert "add_message_files" in CATKIN_TO_AMENT

    def test_generate_messages_mapped(self):
        assert "generate_messages" in CATKIN_TO_AMENT


class TestTransformCmake:
    SIMPLE_CMAKE = """\
cmake_minimum_required(VERSION 3.0.2)
project(ros1_minimal)
find_package(catkin REQUIRED COMPONENTS roscpp std_msgs)
catkin_package()
include_directories(${catkin_INCLUDE_DIRS})
add_executable(talker src/talker.cpp)
target_link_libraries(talker ${catkin_LIBRARIES})
install(TARGETS talker RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
"""

    def test_ament_cmake_find_package_added(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp", "std_msgs"])
        assert "find_package(ament_cmake REQUIRED)" in result

    def test_individual_dep_find_packages_added(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp", "std_msgs"])
        # roscpp → rclcpp
        assert "find_package(rclcpp REQUIRED)" in result
        assert "find_package(std_msgs REQUIRED)" in result

    def test_catkin_find_package_removed(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp", "std_msgs"])
        assert "find_package(catkin" not in result

    def test_catkin_package_replaced_with_ament_package(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp", "std_msgs"])
        assert "ament_package()" in result
        assert "catkin_package()" not in result

    def test_roscpp_remapped_to_rclcpp_in_output(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp", "std_msgs"])
        # The inline remap should replace roscpp with rclcpp in other lines
        assert "roscpp" not in result

    def test_empty_deps_produces_only_ament_cmake(self):
        cmake = "find_package(catkin REQUIRED COMPONENTS)\ncatkin_package()\n"
        result = transform_cmake(cmake, [])
        assert "find_package(ament_cmake REQUIRED)" in result
        assert "ament_package()" in result

    def test_ament_package_not_duplicated(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp"])
        assert result.count("ament_package()") == 1

    def test_ament_target_dependencies_for_include_dirs(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp", "std_msgs"])
        assert "ament_target_dependencies" in result

    def test_ament_target_dependencies_for_link_libraries(self):
        cmake = (
            "find_package(catkin REQUIRED COMPONENTS roscpp)\n"
            "catkin_package()\n"
            "add_executable(talker src/talker.cpp)\n"
            "target_link_libraries(talker ${catkin_LIBRARIES})\n"
        )
        result = transform_cmake(cmake, ["roscpp"])
        assert "ament_target_dependencies(talker" in result

    def test_catkin_include_dirs_variable_removed(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp"])
        assert "${catkin_INCLUDE_DIRS}" not in result

    def test_catkin_libraries_variable_removed(self):
        result = transform_cmake(self.SIMPLE_CMAKE, ["roscpp"])
        assert "${catkin_LIBRARIES}" not in result

    def test_removed_package_skipped(self):
        # dynamic_reconfigure has no ROS2 equivalent → should not appear
        cmake = "find_package(catkin REQUIRED COMPONENTS dynamic_reconfigure)\ncatkin_package()\n"
        result = transform_cmake(cmake, ["dynamic_reconfigure"])
        assert "dynamic_reconfigure" not in result
