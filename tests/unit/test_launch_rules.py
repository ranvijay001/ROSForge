"""Unit tests for rosforge.knowledge.launch_rules."""

from __future__ import annotations

import pytest

from rosforge.knowledge.launch_rules import transform_launch_xml

SIMPLE_LAUNCH = """\
<launch>
  <node pkg="my_pkg" type="talker" name="talker_node" output="screen"/>
</launch>
"""

LAUNCH_WITH_ARGS = """\
<launch>
  <arg name="use_sim_time" default="false" doc="Use simulation time"/>
  <node pkg="my_pkg" type="talker" name="talker" output="screen"/>
</launch>
"""

LAUNCH_WITH_PARAMS = """\
<launch>
  <node pkg="my_pkg" type="talker" name="talker" output="screen">
    <param name="rate" value="10"/>
    <remap from="chatter" to="/robot/chatter"/>
  </node>
</launch>
"""

LAUNCH_WITH_INCLUDE = """\
<launch>
  <include file="$(find other_pkg)/launch/other.launch">
    <arg name="speed" value="1.0"/>
  </include>
</launch>
"""

LAUNCH_WITH_GROUP = """\
<launch>
  <group ns="robot1">
    <node pkg="my_pkg" type="talker" name="talker" output="screen"/>
  </group>
</launch>
"""

LAUNCH_WITH_SUBSTITUTIONS = """\
<launch>
  <arg name="pkg_path" default="$(find my_pkg)/config"/>
  <node pkg="my_pkg" type="node" name="$(arg node_name)" output="screen"/>
</launch>
"""


class TestTransformLaunchXml:
    def test_returns_string(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert isinstance(result, str)

    def test_contains_generate_launch_description(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert "def generate_launch_description()" in result

    def test_contains_launch_description_import(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert "from launch import LaunchDescription" in result

    def test_contains_node_import(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert "from launch_ros.actions import Node" in result

    def test_node_package_mapped(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert '"my_pkg"' in result

    def test_node_executable_mapped(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert '"talker"' in result

    def test_node_name_mapped(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert '"talker_node"' in result

    def test_node_output_preserved(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert '"screen"' in result

    def test_node_class_present(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert "Node(" in result

    def test_arg_declare_emitted(self):
        result = transform_launch_xml(LAUNCH_WITH_ARGS)
        assert "DeclareLaunchArgument" in result

    def test_arg_name_present(self):
        result = transform_launch_xml(LAUNCH_WITH_ARGS)
        assert "use_sim_time" in result

    def test_arg_default_value_present(self):
        result = transform_launch_xml(LAUNCH_WITH_ARGS)
        assert "false" in result

    def test_arg_description_present(self):
        result = transform_launch_xml(LAUNCH_WITH_ARGS)
        assert "Use simulation time" in result

    def test_param_in_node_mapped(self):
        result = transform_launch_xml(LAUNCH_WITH_PARAMS)
        assert "parameters=" in result
        assert '"rate"' in result

    def test_remap_in_node_mapped(self):
        result = transform_launch_xml(LAUNCH_WITH_PARAMS)
        assert "remappings=" in result
        assert '"chatter"' in result
        assert '"/robot/chatter"' in result

    def test_include_launch_description_emitted(self):
        result = transform_launch_xml(LAUNCH_WITH_INCLUDE)
        assert "IncludeLaunchDescription" in result

    def test_include_file_find_substitution(self):
        result = transform_launch_xml(LAUNCH_WITH_INCLUDE)
        assert "FindPackageShare" in result
        assert "'other_pkg'" in result

    def test_include_find_package_share_imported(self):
        result = transform_launch_xml(LAUNCH_WITH_INCLUDE)
        assert "FindPackageShare" in result

    def test_group_ns_comment(self):
        result = transform_launch_xml(LAUNCH_WITH_GROUP)
        assert "robot1" in result

    def test_substitution_arg_converted(self):
        result = transform_launch_xml(LAUNCH_WITH_SUBSTITUTIONS)
        assert "LaunchConfiguration" in result

    def test_substitution_find_converted(self):
        result = transform_launch_xml(LAUNCH_WITH_SUBSTITUTIONS)
        assert "FindPackageShare" in result

    def test_launch_configuration_import(self):
        result = transform_launch_xml(LAUNCH_WITH_SUBSTITUTIONS)
        assert "LaunchConfiguration" in result

    def test_return_launch_description_present(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert "return LaunchDescription([" in result

    def test_closing_bracket_present(self):
        result = transform_launch_xml(SIMPLE_LAUNCH)
        assert "])" in result

    def test_python_launch_description_source_imported(self):
        result = transform_launch_xml(LAUNCH_WITH_INCLUDE)
        assert "PythonLaunchDescriptionSource" in result

    def test_env_element_emits_set_environment_variable(self):
        xml = """\
<launch>
  <env name="MY_VAR" value="hello"/>
  <node pkg="pkg" type="node" name="n"/>
</launch>
"""
        result = transform_launch_xml(xml)
        assert "SetEnvironmentVariable" in result
        assert '"MY_VAR"' in result
        assert '"hello"' in result

    def test_env_element_import_added(self):
        xml = """\
<launch>
  <env name="X" value="1"/>
</launch>
"""
        result = transform_launch_xml(xml)
        assert "SetEnvironmentVariable" in result

    def test_group_ns_emits_push_ros_namespace(self):
        result = transform_launch_xml(LAUNCH_WITH_GROUP)
        assert "PushRosNamespace" in result
        assert "GroupAction" in result

    def test_group_ns_value_present(self):
        result = transform_launch_xml(LAUNCH_WITH_GROUP)
        assert "robot1" in result

    def test_push_ros_namespace_import_added(self):
        result = transform_launch_xml(LAUNCH_WITH_GROUP)
        assert "PushRosNamespace" in result

    def test_node_inside_group_ns_present(self):
        result = transform_launch_xml(LAUNCH_WITH_GROUP)
        assert "Node(" in result
        assert '"talker"' in result

    def test_env_in_group(self):
        xml = """\
<launch>
  <group ns="robot">
    <env name="ROBOT_VAR" value="42"/>
    <node pkg="pkg" type="node" name="n"/>
  </group>
</launch>
"""
        result = transform_launch_xml(xml)
        assert "SetEnvironmentVariable" in result
        assert '"ROBOT_VAR"' in result
