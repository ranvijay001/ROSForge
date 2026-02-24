"""Integration tests for test fixtures — verify fixture files are well-formed."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestRos1MinimalFixture:
    def test_package_xml_exists(self) -> None:
        assert (FIXTURES / "ros1_minimal" / "package.xml").exists()

    def test_cmakelists_exists(self) -> None:
        assert (FIXTURES / "ros1_minimal" / "CMakeLists.txt").exists()

    def test_cpp_source_exists(self) -> None:
        assert (FIXTURES / "ros1_minimal" / "src" / "talker.cpp").exists()

    def test_package_xml_is_valid_xml(self) -> None:
        path = FIXTURES / "ros1_minimal" / "package.xml"
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.tag == "package"

    def test_package_has_name(self) -> None:
        path = FIXTURES / "ros1_minimal" / "package.xml"
        tree = ET.parse(path)
        root = tree.getroot()
        name_elem = root.find("name")
        assert name_elem is not None
        assert name_elem.text


class TestRos1PythonFixture:
    def test_package_xml_exists(self) -> None:
        assert (FIXTURES / "ros1_python" / "package.xml").exists()

    def test_cmakelists_exists(self) -> None:
        assert (FIXTURES / "ros1_python" / "CMakeLists.txt").exists()

    def test_python_script_exists(self) -> None:
        assert (FIXTURES / "ros1_python" / "scripts" / "listener.py").exists()

    def test_python_script_uses_rospy(self) -> None:
        content = (FIXTURES / "ros1_python" / "scripts" / "listener.py").read_text()
        assert "rospy" in content


class TestRos1WithMsgsFixture:
    def test_directory_exists(self) -> None:
        assert (FIXTURES / "ros1_with_msgs").is_dir()

    def test_package_xml_exists(self) -> None:
        assert (FIXTURES / "ros1_with_msgs" / "package.xml").exists()

    def test_cmakelists_exists(self) -> None:
        assert (FIXTURES / "ros1_with_msgs" / "CMakeLists.txt").exists()

    def test_msg_files_exist(self) -> None:
        assert (FIXTURES / "ros1_with_msgs" / "msg" / "Greeting.msg").exists()
        assert (FIXTURES / "ros1_with_msgs" / "msg" / "Status.msg").exists()

    def test_srv_file_exists(self) -> None:
        assert (FIXTURES / "ros1_with_msgs" / "srv" / "SayHello.srv").exists()

    def test_srv_has_separator(self) -> None:
        content = (FIXTURES / "ros1_with_msgs" / "srv" / "SayHello.srv").read_text()
        assert "---" in content

    def test_package_xml_has_message_generation(self) -> None:
        content = (FIXTURES / "ros1_with_msgs" / "package.xml").read_text()
        assert "message_generation" in content

    def test_cmakelists_has_add_message_files(self) -> None:
        content = (FIXTURES / "ros1_with_msgs" / "CMakeLists.txt").read_text()
        assert "add_message_files" in content


class TestRos1LaunchFixture:
    def test_directory_exists(self) -> None:
        assert (FIXTURES / "ros1_launch").is_dir()

    def test_package_xml_exists(self) -> None:
        assert (FIXTURES / "ros1_launch" / "package.xml").exists()

    def test_launch_file_exists(self) -> None:
        assert (FIXTURES / "ros1_launch" / "launch" / "robot.launch").exists()

    def test_launch_file_is_valid_xml(self) -> None:
        path = FIXTURES / "ros1_launch" / "launch" / "robot.launch"
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.tag == "launch"

    def test_launch_has_node_element(self) -> None:
        path = FIXTURES / "ros1_launch" / "launch" / "robot.launch"
        tree = ET.parse(path)
        root = tree.getroot()
        nodes = root.findall(".//node")
        assert len(nodes) > 0

    def test_launch_has_arg_element(self) -> None:
        path = FIXTURES / "ros1_launch" / "launch" / "robot.launch"
        tree = ET.parse(path)
        root = tree.getroot()
        args = root.findall(".//arg")
        assert len(args) > 0


class TestRos1MixedFixture:
    def test_directory_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed").is_dir()

    def test_package_xml_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed" / "package.xml").exists()

    def test_cmakelists_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed" / "CMakeLists.txt").exists()

    def test_cpp_source_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed" / "src" / "sensor_node.cpp").exists()

    def test_python_script_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed" / "scripts" / "monitor.py").exists()

    def test_launch_file_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed" / "launch" / "mixed.launch").exists()

    def test_msg_file_exists(self) -> None:
        assert (FIXTURES / "ros1_mixed" / "msg" / "Alert.msg").exists()

    def test_cpp_uses_ros_includes(self) -> None:
        content = (FIXTURES / "ros1_mixed" / "src" / "sensor_node.cpp").read_text()
        assert "ros/ros.h" in content

    def test_python_uses_rospy(self) -> None:
        content = (FIXTURES / "ros1_mixed" / "scripts" / "monitor.py").read_text()
        assert "rospy" in content

    def test_mixed_has_both_roscpp_and_rospy(self) -> None:
        content = (FIXTURES / "ros1_mixed" / "package.xml").read_text()
        assert "roscpp" in content
        assert "rospy" in content
