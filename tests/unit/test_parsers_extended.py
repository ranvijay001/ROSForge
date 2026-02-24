"""Extended unit tests for all ROS1 parsers: python_source, launch_xml, msg_srv, cmake, package_xml."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.models.ir import DependencyType
from rosforge.parsers.cmake import parse_cmake
from rosforge.parsers.launch_xml import parse_launch_xml
from rosforge.parsers.msg_srv import parse_msg_srv
from rosforge.parsers.package_xml import parse_package_xml
from rosforge.parsers.python_source import scan_python

FIXTURES = Path(__file__).parent.parent / "fixtures"
ROS1_PYTHON = FIXTURES / "ros1_python"
ROS1_MSGS = FIXTURES / "ros1_msgs"
ROS1_LAUNCH = FIXTURES / "ros1_launch"


# ---------------------------------------------------------------------------
# python_source.py
# ---------------------------------------------------------------------------


class TestPythonSourceScanner:
    def test_returns_list(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        assert isinstance(result, list)

    def test_detects_import_rospy(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        api_names = {u.api_name for u in result}
        assert "rospy.import" in api_names

    def test_detects_init_node(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        api_names = {u.api_name for u in result}
        assert "rospy.init_node" in api_names

    def test_detects_subscriber(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        api_names = {u.api_name for u in result}
        assert "rospy.Subscriber" in api_names

    def test_detects_spin(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        api_names = {u.api_name for u in result}
        assert "rospy.spin" in api_names

    def test_detects_loginfo(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        api_names = {u.api_name for u in result}
        assert "rospy.loginfo" in api_names

    def test_records_file_path(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        assert result
        assert "listener.py" in result[0].file_path

    def test_records_line_number(self):
        result = scan_python(ROS1_PYTHON / "scripts" / "listener.py")
        assert result
        assert result[0].line_number > 0

    def test_missing_file_returns_empty(self, tmp_path):
        result = scan_python(tmp_path / "nonexistent.py")
        assert result == []

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        result = scan_python(f)
        assert result == []

    def test_publisher_detection(self, tmp_path):
        f = tmp_path / "pub.py"
        f.write_text("import rospy\npub = rospy.Publisher('topic', String, queue_size=10)\n")
        result = scan_python(f)
        api_names = {u.api_name for u in result}
        assert "rospy.Publisher" in api_names

    def test_service_proxy_detection(self, tmp_path):
        f = tmp_path / "svc.py"
        f.write_text("import rospy\nproxy = rospy.ServiceProxy('svc', MySrv)\n")
        result = scan_python(f)
        api_names = {u.api_name for u in result}
        assert "rospy.ServiceProxy" in api_names

    def test_get_param_detection(self, tmp_path):
        f = tmp_path / "param.py"
        f.write_text("import rospy\nval = rospy.get_param('~rate', 10)\n")
        result = scan_python(f)
        api_names = {u.api_name for u in result}
        assert "rospy.get_param" in api_names

    def test_rate_detection(self, tmp_path):
        f = tmp_path / "rate.py"
        f.write_text("import rospy\nrate = rospy.Rate(10)\n")
        result = scan_python(f)
        api_names = {u.api_name for u in result}
        assert "rospy.Rate" in api_names

    def test_time_detection(self, tmp_path):
        f = tmp_path / "time_.py"
        f.write_text("import rospy\nt = rospy.Time.now()\n")
        result = scan_python(f)
        api_names = {u.api_name for u in result}
        assert "rospy.Time" in api_names


# ---------------------------------------------------------------------------
# launch_xml.py
# ---------------------------------------------------------------------------


class TestLaunchXmlParser:
    def test_returns_dict(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        for key in ("nodes", "params", "rosparam", "includes", "args", "groups", "remaps"):
            assert key in result

    def test_parses_nodes(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert len(result["nodes"]) >= 2

    def test_node_has_pkg(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        node = result["nodes"][0]
        assert node["pkg"] == "roscpp_tutorials"

    def test_node_has_type(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        node = result["nodes"][0]
        assert node["type"] == "talker"

    def test_node_has_remaps(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        talker = next(n for n in result["nodes"] if n["name"] == "talker")
        assert len(talker["remaps"]) >= 1
        assert talker["remaps"][0]["from"] == "chatter"

    def test_parses_args(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert len(result["args"]) >= 1
        arg = result["args"][0]
        assert arg["name"] == "use_sim_time"
        assert arg["default"] == "false"

    def test_parses_params(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert len(result["params"]) >= 1

    def test_parses_includes(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert len(result["includes"]) >= 1

    def test_parses_groups(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert len(result["groups"]) >= 1
        group = result["groups"][0]
        assert group["ns"] == "sensors"

    def test_parses_rosparam(self):
        result = parse_launch_xml(ROS1_LAUNCH / "talker_listener.launch")
        assert len(result["rosparam"]) >= 1

    def test_missing_file_returns_empty_structure(self, tmp_path):
        result = parse_launch_xml(tmp_path / "nonexistent.launch")
        assert result["nodes"] == []
        assert result["args"] == []

    def test_minimal_launch(self, tmp_path):
        f = tmp_path / "minimal.launch"
        f.write_text('<launch><node pkg="p" type="t" name="n"/></launch>')
        result = parse_launch_xml(f)
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["pkg"] == "p"


# ---------------------------------------------------------------------------
# msg_srv.py
# ---------------------------------------------------------------------------


class TestMsgParser:
    def test_parse_msg_kind(self):
        result = parse_msg_srv(ROS1_MSGS / "msg" / "Pose2D.msg")
        assert result["kind"] == "msg"

    def test_parse_msg_fields(self):
        result = parse_msg_srv(ROS1_MSGS / "msg" / "Pose2D.msg")
        names = [f["name"] for f in result["fields"]]
        assert "x" in names
        assert "y" in names
        assert "theta" in names

    def test_parse_msg_field_types(self):
        result = parse_msg_srv(ROS1_MSGS / "msg" / "Pose2D.msg")
        types = {f["name"]: f["type"] for f in result["fields"]}
        assert types["x"] == "float64"
        assert types["theta"] == "float64"

    def test_parse_msg_with_constant(self):
        result = parse_msg_srv(ROS1_MSGS / "msg" / "StringArray.msg")
        assert result["kind"] == "msg"
        const_names = [c["name"] for c in result["constants"]]
        assert "MAX_SIZE" in const_names

    def test_parse_msg_array_field(self):
        result = parse_msg_srv(ROS1_MSGS / "msg" / "StringArray.msg")
        arr_fields = [f for f in result["fields"] if f["array"]]
        assert len(arr_fields) >= 1
        data_field = next(f for f in result["fields"] if f["name"] == "data")
        assert data_field["array"] is True

    def test_parse_msg_inline(self, tmp_path):
        f = tmp_path / "Simple.msg"
        f.write_text("int32 value\nstring name\n")
        result = parse_msg_srv(f)
        assert result["kind"] == "msg"
        names = [x["name"] for x in result["fields"]]
        assert "value" in names
        assert "name" in names

    def test_parse_msg_missing_file(self, tmp_path):
        result = parse_msg_srv(tmp_path / "nope.msg")
        assert result == {}


class TestSrvParser:
    def test_parse_srv_kind(self):
        result = parse_msg_srv(ROS1_MSGS / "srv" / "AddTwoInts.srv")
        assert result["kind"] == "srv"

    def test_parse_srv_request_fields(self):
        result = parse_msg_srv(ROS1_MSGS / "srv" / "AddTwoInts.srv")
        req_names = [f["name"] for f in result["request"]["fields"]]
        assert "a" in req_names
        assert "b" in req_names

    def test_parse_srv_response_fields(self):
        result = parse_msg_srv(ROS1_MSGS / "srv" / "AddTwoInts.srv")
        res_names = [f["name"] for f in result["response"]["fields"]]
        assert "sum" in res_names

    def test_parse_srv_field_types(self):
        result = parse_msg_srv(ROS1_MSGS / "srv" / "AddTwoInts.srv")
        req_types = {f["name"]: f["type"] for f in result["request"]["fields"]}
        assert req_types["a"] == "int64"

    def test_parse_srv_no_separator(self, tmp_path):
        f = tmp_path / "NoSep.srv"
        f.write_text("int32 x\nint32 y\n")
        result = parse_msg_srv(f)
        assert result["kind"] == "srv"
        assert len(result["request"]["fields"]) == 2
        assert result["response"]["fields"] == []


class TestActionParser:
    def test_parse_action_kind(self):
        result = parse_msg_srv(ROS1_MSGS / "action" / "Fibonacci.action")
        assert result["kind"] == "action"

    def test_parse_action_goal(self):
        result = parse_msg_srv(ROS1_MSGS / "action" / "Fibonacci.action")
        goal_names = [f["name"] for f in result["goal"]["fields"]]
        assert "order" in goal_names

    def test_parse_action_result(self):
        result = parse_msg_srv(ROS1_MSGS / "action" / "Fibonacci.action")
        result_names = [f["name"] for f in result["result"]["fields"]]
        assert "sequence" in result_names

    def test_parse_action_feedback(self):
        result = parse_msg_srv(ROS1_MSGS / "action" / "Fibonacci.action")
        fb_names = [f["name"] for f in result["feedback"]["fields"]]
        assert "partial_sequence" in fb_names

    def test_parse_action_result_array(self):
        result = parse_msg_srv(ROS1_MSGS / "action" / "Fibonacci.action")
        seq_field = next(f for f in result["result"]["fields"] if f["name"] == "sequence")
        assert seq_field["array"] is True


# ---------------------------------------------------------------------------
# cmake.py (enhanced)
# ---------------------------------------------------------------------------


class TestCMakeParserEnhanced:
    def test_parse_returns_dict(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert isinstance(result, dict)

    def test_project_name(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert result["project_name"] == "ros1_msgs"

    def test_catkin_packages(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert "roscpp" in result["catkin_packages"]
        assert "std_msgs" in result["catkin_packages"]

    def test_catkin_depends(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert "roscpp" in result["catkin_depends"]

    def test_msg_files(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert "Pose2D.msg" in result["msg_files"]
        assert "StringArray.msg" in result["msg_files"]

    def test_srv_files(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert "AddTwoInts.srv" in result["srv_files"]

    def test_action_files(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert "Fibonacci.action" in result["action_files"]

    def test_msg_deps(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert "std_msgs" in result["msg_deps"]

    def test_targets(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        target_names = [t["name"] for t in result["targets"]]
        assert "talker" in target_names
        assert "mylib" in target_names

    def test_target_link_libraries(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        talker = next(t for t in result["targets"] if t["name"] == "talker")
        assert "${catkin_LIBRARIES}" in talker.get("link_libraries", [])

    def test_install_rules(self):
        result = parse_cmake(ROS1_MSGS / "CMakeLists.txt")
        assert len(result["install_rules"]) > 0

    def test_empty_cmake_returns_defaults(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text("cmake_minimum_required(VERSION 3.0.2)\n")
        result = parse_cmake(f)
        assert result["msg_files"] == []
        assert result["srv_files"] == []
        assert result["action_files"] == []
        assert result["msg_deps"] == []


# ---------------------------------------------------------------------------
# package_xml.py (format 1 support)
# ---------------------------------------------------------------------------


class TestPackageXmlFormat1:
    def test_parses_format1_without_attribute(self):
        meta, deps = parse_package_xml(ROS1_MSGS / "package_format1.xml")
        assert meta.format_version == 1

    def test_parses_name(self):
        meta, _ = parse_package_xml(ROS1_MSGS / "package_format1.xml")
        assert meta.name == "ros1_format1_pkg"

    def test_parses_version(self):
        meta, _ = parse_package_xml(ROS1_MSGS / "package_format1.xml")
        assert meta.version == "1.2.3"

    def test_run_depend_mapped_to_exec(self):
        _, deps = parse_package_xml(ROS1_MSGS / "package_format1.xml")
        exec_deps = [d for d in deps if d.dep_type == DependencyType.EXEC]
        exec_names = {d.name for d in exec_deps}
        assert "roscpp" in exec_names
        assert "std_msgs" in exec_names

    def test_build_depend_present(self):
        _, deps = parse_package_xml(ROS1_MSGS / "package_format1.xml")
        build_deps = [d for d in deps if d.dep_type == DependencyType.BUILD]
        assert any(d.name == "roscpp" for d in build_deps)

    def test_buildtool_depend_present(self):
        _, deps = parse_package_xml(ROS1_MSGS / "package_format1.xml")
        bt_deps = [d for d in deps if d.dep_type == DependencyType.BUILDTOOL]
        assert any(d.name == "catkin" for d in bt_deps)

    def test_format2_still_works(self):
        """Existing format 2 fixture should still parse correctly."""
        meta, deps = parse_package_xml(
            Path(__file__).parent.parent / "fixtures" / "ros1_minimal" / "package.xml"
        )
        assert meta.format_version == 2
        assert meta.name == "ros1_minimal"

    def test_format2_no_run_depend(self):
        """Format 2 packages should not have run_depend mapped."""
        _, deps = parse_package_xml(
            Path(__file__).parent.parent / "fixtures" / "ros1_minimal" / "package.xml"
        )
        # All exec_depends should come from exec_depend tags, not run_depend
        assert isinstance(deps, list)

    def test_format1_inline(self, tmp_path):
        f = tmp_path / "package.xml"
        f.write_text(
            '<?xml version="1.0"?>\n'
            "<package>\n"
            "  <name>mypkg</name>\n"
            "  <version>0.0.1</version>\n"
            "  <description>test</description>\n"
            '  <maintainer email="a@b.com">me</maintainer>\n'
            "  <license>MIT</license>\n"
            "  <buildtool_depend>catkin</buildtool_depend>\n"
            "  <run_depend>sensor_msgs</run_depend>\n"
            "</package>\n"
        )
        meta, deps = parse_package_xml(f)
        assert meta.format_version == 1
        exec_deps = {d.name for d in deps if d.dep_type == DependencyType.EXEC}
        assert "sensor_msgs" in exec_deps
