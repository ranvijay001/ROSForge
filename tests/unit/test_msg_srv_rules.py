"""Unit tests for rosforge.knowledge.msg_srv_rules."""

from __future__ import annotations

import pytest

from rosforge.knowledge.msg_srv_rules import (
    transform_action,
    transform_msg,
    transform_srv,
)


class TestTransformMsg:
    def test_returns_string(self):
        result = transform_msg("std_msgs/String data\n")
        assert isinstance(result, str)

    def test_primitive_type_unchanged(self):
        result = transform_msg("float64 x\n")
        assert "float64 x" in result

    def test_string_type_unchanged(self):
        result = transform_msg("string name\n")
        assert "string name" in result

    def test_header_remapped(self):
        result = transform_msg("Header header\n")
        assert "std_msgs/msg/Header header" in result
        assert "Header header" not in result or "std_msgs/msg/Header header" in result

    def test_time_remapped(self):
        result = transform_msg("time stamp\n")
        assert "builtin_interfaces/msg/Time stamp" in result

    def test_duration_remapped(self):
        result = transform_msg("duration timeout\n")
        assert "builtin_interfaces/msg/Duration timeout" in result

    def test_pkg_qualified_type_gets_msg_segment(self):
        result = transform_msg("geometry_msgs/Point position\n")
        assert "geometry_msgs/msg/Point position" in result

    def test_already_qualified_type_unchanged(self):
        result = transform_msg("geometry_msgs/msg/Point position\n")
        assert "geometry_msgs/msg/Point position" in result

    def test_array_type_preserved(self):
        result = transform_msg("float64[] values\n")
        assert "float64[] values" in result

    def test_fixed_array_type_preserved(self):
        result = transform_msg("uint8[3] rgb\n")
        assert "uint8[3] rgb" in result

    def test_pkg_qualified_array_remapped(self):
        result = transform_msg("geometry_msgs/Point[] points\n")
        assert "geometry_msgs/msg/Point[] points" in result

    def test_comment_lines_preserved(self):
        msg = "# This is a comment\nfloat64 x\n"
        result = transform_msg(msg)
        assert "# This is a comment" in result

    def test_empty_lines_preserved(self):
        msg = "float64 x\n\nfloat64 y\n"
        result = transform_msg(msg)
        assert "\n\n" in result

    def test_multiple_fields(self):
        msg = "Header header\nfloat64 x\ngeometry_msgs/Point p\n"
        result = transform_msg(msg)
        assert "std_msgs/msg/Header header" in result
        assert "float64 x" in result
        assert "geometry_msgs/msg/Point p" in result


class TestTransformSrv:
    def test_returns_string(self):
        result = transform_srv("float64 x\n---\nbool success\n")
        assert isinstance(result, str)

    def test_separator_preserved(self):
        result = transform_srv("float64 x\n---\nbool success\n")
        assert "---" in result

    def test_request_type_remapped(self):
        result = transform_srv("Header header\n---\nbool success\n")
        assert "std_msgs/msg/Header header" in result

    def test_response_type_remapped(self):
        result = transform_srv("float64 x\n---\ngeometry_msgs/Point result\n")
        assert "geometry_msgs/msg/Point result" in result

    def test_primitive_types_in_both_sections(self):
        result = transform_srv("int32 a\n---\nint32 b\n")
        assert result.count("int32") == 2

    def test_no_separator_still_works(self):
        result = transform_srv("float64 value\n")
        assert "float64 value" in result

    def test_time_in_request(self):
        result = transform_srv("time stamp\n---\nbool ok\n")
        assert "builtin_interfaces/msg/Time stamp" in result


class TestTransformAction:
    def test_returns_string(self):
        action = "int32 goal\n---\nbool success\n---\nfloat32 feedback\n"
        result = transform_action(action)
        assert isinstance(result, str)

    def test_three_sections_separated(self):
        action = "int32 goal\n---\nbool success\n---\nfloat32 feedback\n"
        result = transform_action(action)
        assert result.count("---") == 2

    def test_goal_type_remapped(self):
        action = "geometry_msgs/Pose target\n---\nbool success\n---\nfloat32 pct\n"
        result = transform_action(action)
        assert "geometry_msgs/msg/Pose target" in result

    def test_result_type_remapped(self):
        action = "int32 goal\n---\ngeometry_msgs/Pose final_pose\n---\nfloat32 pct\n"
        result = transform_action(action)
        assert "geometry_msgs/msg/Pose final_pose" in result

    def test_feedback_type_remapped(self):
        action = "int32 goal\n---\nbool done\n---\ngeometry_msgs/Point current\n"
        result = transform_action(action)
        assert "geometry_msgs/msg/Point current" in result

    def test_header_in_goal(self):
        action = "Header header\nint32 goal\n---\nbool done\n---\nfloat32 pct\n"
        result = transform_action(action)
        assert "std_msgs/msg/Header header" in result

    def test_time_in_feedback(self):
        action = "int32 goal\n---\nbool done\n---\ntime stamp\nfloat32 pct\n"
        result = transform_action(action)
        assert "builtin_interfaces/msg/Time stamp" in result
