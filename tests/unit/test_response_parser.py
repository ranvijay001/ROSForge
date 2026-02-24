"""Tests for the enhanced ResponseParser, confidence scoring, and cost estimator."""

from __future__ import annotations

import json

import pytest

from rosforge.engine.response_parser import (
    _extract_dict,
    _extract_nested_fences,
    _recover_partial_json,
    compute_confidence,
    estimate_cost_usd,
    parse_analyze_response,
    parse_structured_output,
    parse_transform_response,
)
from rosforge.models.plan import TransformStrategy

# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------


class TestExtractDict:
    def test_plain_json(self):
        data = {"key": "value", "num": 42}
        result = _extract_dict(json.dumps(data))
        assert result == data

    def test_json_fence(self):
        payload = {"source_path": "src/node.cpp"}
        text = f"Some preamble\n```json\n{json.dumps(payload)}\n```\nTrailing text"
        result = _extract_dict(text)
        assert result == payload

    def test_generic_fence(self):
        payload = {"key": "val"}
        text = f"```\n{json.dumps(payload)}\n```"
        result = _extract_dict(text)
        assert result == payload

    def test_partial_json_recovery(self):
        # Trailing garbage after valid JSON
        payload = {"recovered": True}
        text = json.dumps(payload) + "\n\nSome trailing explanation."
        result = _extract_dict(text)
        assert result is not None
        assert result.get("recovered") is True

    def test_returns_none_for_garbage(self):
        result = _extract_dict("This is not JSON at all.")
        assert result is None

    def test_returns_none_for_empty(self):
        result = _extract_dict("")
        assert result is None


class TestExtractNestedFences:
    def test_multiple_fences_returns_first_valid(self):
        payload = {"first": True}
        text = f"```json\nnot valid json\n```\n```json\n{json.dumps(payload)}\n```"
        result = _extract_nested_fences(text)
        assert result == payload

    def test_language_tagged_fence(self):
        payload = {"tagged": True}
        text = f"```python\n# not json\n```\n```json\n{json.dumps(payload)}\n```"
        result = _extract_nested_fences(text)
        assert result == payload

    def test_no_fences_returns_none(self):
        result = _extract_nested_fences("plain text no fences")
        assert result is None


class TestRecoverPartialJson:
    def test_recovers_object_with_trailing_text(self):
        payload = {"partial": "recovery"}
        text = json.dumps(payload) + "\n\nSome extra text that is not JSON."
        result = _recover_partial_json(text)
        assert result is not None
        assert result.get("partial") == "recovery"

    def test_returns_none_when_no_brace(self):
        result = _recover_partial_json("no braces here at all")
        assert result is None


# ---------------------------------------------------------------------------
# parse_transform_response
# ---------------------------------------------------------------------------


class TestParseTransformResponse:
    def _valid_payload(self) -> dict:
        return {
            "source_path": "src/node.cpp",
            "target_path": "src/node.cpp",
            "transformed_content": "#include <rclcpp/rclcpp.hpp>",
            "confidence": 0.85,
            "strategy_used": "ai_driven",
            "warnings": [],
            "changes": [{"description": "Updated header", "line_range": "1", "reason": "ROS2 API"}],
        }

    def test_parses_plain_json(self):
        result = parse_transform_response(json.dumps(self._valid_payload()))
        assert result.source_path == "src/node.cpp"
        assert result.confidence == 0.85
        assert len(result.changes) == 1

    def test_parses_fenced_json(self):
        payload = self._valid_payload()
        text = f"Here is the result:\n```json\n{json.dumps(payload)}\n```"
        result = parse_transform_response(text)
        assert result.source_path == "src/node.cpp"

    def test_parse_failure_returns_stub(self):
        result = parse_transform_response("This is not JSON.")
        assert result.confidence == 0.0
        assert "parse_failure" in result.warnings[0]
        assert result.transformed_content == "This is not JSON."

    def test_missing_fields_use_defaults(self):
        partial = {"source_path": "src/node.cpp"}
        result = parse_transform_response(json.dumps(partial))
        assert result.target_path == ""
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# parse_analyze_response
# ---------------------------------------------------------------------------


class TestParseAnalyzeResponse:
    def _valid_payload(self) -> dict:
        return {
            "package_name": "my_pkg",
            "target_ros2_distro": "humble",
            "overall_confidence": 0.7,
            "summary": "Simple package",
            "warnings": ["Check launch files"],
            "actions": [
                {
                    "source_path": "src/node.cpp",
                    "target_path": "src/node.cpp",
                    "strategy": "ai_driven",
                    "description": "Migrate roscpp to rclcpp",
                    "estimated_complexity": 2,
                    "confidence": 0.8,
                }
            ],
        }

    def test_parses_correctly(self):
        result = parse_analyze_response(json.dumps(self._valid_payload()))
        assert result.package_name == "my_pkg"
        assert result.overall_confidence == 0.7
        assert len(result.actions) == 1
        assert result.actions[0].strategy == TransformStrategy.AI_DRIVEN

    def test_invalid_strategy_defaults_to_ai_driven(self):
        payload = self._valid_payload()
        payload["actions"][0]["strategy"] = "invalid_value"
        result = parse_analyze_response(json.dumps(payload))
        assert result.actions[0].strategy == TransformStrategy.AI_DRIVEN

    def test_parse_failure_returns_empty_plan(self):
        result = parse_analyze_response("garbage text")
        assert result.package_name == ""
        assert "parse_failure" in result.warnings[0]

    def test_fenced_response(self):
        payload = self._valid_payload()
        text = f"```json\n{json.dumps(payload)}\n```"
        result = parse_analyze_response(text)
        assert result.package_name == "my_pkg"


# ---------------------------------------------------------------------------
# compute_confidence
# ---------------------------------------------------------------------------


class TestComputeConfidence:
    def test_empty_inputs_returns_zero(self):
        assert compute_confidence("", "") == 0.0
        assert compute_confidence("content", "") == 0.0
        assert compute_confidence("", "content") == 0.0

    def test_identical_returns_low_score(self):
        # Unchanged file should score low (likely no migration happened)
        content = "#include <ros/ros.h>\nint main() {}"
        score = compute_confidence(content, content)
        assert score < 0.5

    def test_ros2_content_scores_higher(self):
        original = "#include <ros/ros.h>\nros::NodeHandle nh;\nnh.advertise<std_msgs::String>('topic', 10);"
        transformed = (
            "#include <rclcpp/rclcpp.hpp>\n"
            "auto node = std::make_shared<rclcpp::Node>('node');\n"
            "node->create_publisher<std_msgs::msg::String>('topic', 10);\n"
            "rclcpp::spin(node);\n"
            "node->get_logger();"
        )
        score = compute_confidence(transformed, original)
        assert score > 0.3

    def test_ros1_markers_penalise_score(self):
        # Transformed content still has ROS1 patterns
        original = "#include <ros/ros.h>"
        transformed = "ros::NodeHandle nh; nh.advertise<T>(); catkin_package();"
        score = compute_confidence(transformed, original)
        # Score should be penalised
        assert score < 0.8

    def test_score_in_valid_range(self):
        for orig, trans in [
            ("hello", "world"),
            ("#include <ros/ros.h>", "#include <rclcpp/rclcpp.hpp>"),
            ("rospy.init_node('n')", "rclpy.init()"),
        ]:
            s = compute_confidence(trans, orig)
            assert 0.0 <= s <= 1.0


# ---------------------------------------------------------------------------
# estimate_cost_usd
# ---------------------------------------------------------------------------


class TestEstimateCostUsd:
    def test_zero_tokens_is_zero_cost(self):
        assert estimate_cost_usd("claude-3-5-sonnet", 0, 0) == 0.0

    def test_known_engine_produces_nonzero_cost(self):
        cost = estimate_cost_usd("claude-3-5-sonnet", 1000, 500)
        assert cost > 0.0

    def test_unknown_engine_uses_default(self):
        cost_unknown = estimate_cost_usd("totally-unknown-model", 1000, 500)
        assert cost_unknown > 0.0

    def test_prefix_matching(self):
        # Full versioned name should match prefix
        cost_short = estimate_cost_usd("claude-3-5-sonnet", 1000, 500)
        cost_long = estimate_cost_usd("claude-3-5-sonnet-20241022", 1000, 500)
        assert cost_short == cost_long

    def test_output_tokens_cost_more_than_input(self):
        # For most models output is more expensive than input
        input_only = estimate_cost_usd("claude-3-5-sonnet", 1000, 0)
        output_only = estimate_cost_usd("claude-3-5-sonnet", 0, 1000)
        assert output_only > input_only

    def test_gpt4o_mini_cheaper_than_gpt4o(self):
        cost_mini = estimate_cost_usd("gpt-4o-mini", 100000, 20000)
        cost_full = estimate_cost_usd("gpt-4o", 100000, 20000)
        assert cost_mini < cost_full


# ---------------------------------------------------------------------------
# parse_structured_output
# ---------------------------------------------------------------------------


class TestParseStructuredOutput:
    def test_returns_expected_keys(self):
        payload = {"source_path": "src/node.cpp", "confidence": 0.9}
        result = parse_structured_output(json.dumps(payload), ["source_path", "confidence"])
        assert result["source_path"] == "src/node.cpp"
        assert result["confidence"] == 0.9

    def test_missing_keys_return_none(self):
        payload = {"source_path": "src/node.cpp"}
        result = parse_structured_output(json.dumps(payload), ["source_path", "confidence"])
        assert result["confidence"] is None

    def test_parse_failure_fills_none_and_error_key(self):
        result = parse_structured_output("not json", ["source_path", "confidence"])
        assert result["source_path"] is None
        assert result["confidence"] is None
        assert "_parse_error" in result
