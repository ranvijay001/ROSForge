"""Tests for the enhanced PromptBuilder."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.models.ir import (
    FileType,
    PackageIR,
    PackageMetadata,
    ROSAPIUsage,
    SourceFile,
)
from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source_file(
    path: str = "src/node.cpp",
    file_type: FileType = FileType.CPP,
    content: str = "#include <ros/ros.h>\nint main() {}",
    api_count: int = 0,
) -> SourceFile:
    usages = [
        ROSAPIUsage(api_name="ros::init", file_path=path, line_number=i) for i in range(api_count)
    ]
    return SourceFile(
        relative_path=path,
        file_type=file_type,
        content=content,
        line_count=content.count("\n") + 1,
        api_usages=usages,
    )


def _make_ir(name: str = "test_pkg") -> PackageIR:
    return PackageIR(
        source_path=Path("/tmp/test_pkg"),
        metadata=PackageMetadata(name=name, version="1.0.0"),
        total_files=2,
        total_lines=50,
    )


def _make_plan() -> MigrationPlan:
    return MigrationPlan(
        package_name="test_pkg",
        actions=[
            TransformAction(
                source_path="src/node.cpp",
                target_path="src/node.cpp",
                strategy=TransformStrategy.AI_DRIVEN,
                estimated_complexity=2,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_empty_string(self):
        assert PromptBuilder.estimate_tokens("") == 0

    def test_rough_estimate(self):
        text = "a" * 400
        assert PromptBuilder.estimate_tokens(text) == 100

    def test_estimate_file_tokens_includes_overhead(self):
        f = _make_source_file(content="x" * 400)
        tokens = PromptBuilder.estimate_file_tokens(f)
        # content tokens (100) + overhead (50)
        assert tokens == 150


# ---------------------------------------------------------------------------
# Analyze prompt
# ---------------------------------------------------------------------------


class TestBuildAnalyzePrompt:
    def test_returns_two_strings(self):
        pb = PromptBuilder()
        ir = _make_ir()
        system, user = pb.build_analyze_prompt(ir)
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_contains_json_schema(self):
        pb = PromptBuilder()
        system, _ = pb.build_analyze_prompt(_make_ir())
        assert "package_name" in system
        assert "actions" in system

    def test_user_contains_package_name(self):
        pb = PromptBuilder()
        _, user = pb.build_analyze_prompt(_make_ir("my_package"))
        assert "my_package" in user

    def test_system_contains_knowledge_tables(self):
        pb = PromptBuilder()
        system, _ = pb.build_analyze_prompt(_make_ir())
        assert "rclcpp" in system or "rclpy" in system or "ament" in system


# ---------------------------------------------------------------------------
# Transform prompt — per-file-type
# ---------------------------------------------------------------------------


class TestBuildTransformPromptFileType:
    def test_cpp_system_contains_rclcpp(self):
        pb = PromptBuilder()
        f = _make_source_file("src/node.cpp", FileType.CPP)
        plan = _make_plan()
        system, _ = pb.build_transform_prompt(f, plan)
        assert "rclcpp" in system.lower() or "roscpp" in system.lower()

    def test_python_system_contains_rclpy(self):
        pb = PromptBuilder()
        f = _make_source_file("nodes/listener.py", FileType.PYTHON)
        plan = _make_plan()
        system, _ = pb.build_transform_prompt(f, plan)
        assert "rclpy" in system.lower() or "rospy" in system.lower()

    def test_launch_system_contains_launch_description(self):
        pb = PromptBuilder()
        f = _make_source_file("launch/start.launch", FileType.LAUNCH_XML)
        plan = _make_plan()
        system, _ = pb.build_transform_prompt(f, plan)
        assert "LaunchDescription" in system or "launch" in system.lower()

    def test_cmake_system_contains_ament(self):
        pb = PromptBuilder()
        f = _make_source_file("CMakeLists.txt", FileType.CMAKE)
        plan = _make_plan()
        system, _ = pb.build_transform_prompt(f, plan)
        assert "ament" in system.lower()

    def test_user_contains_file_path(self):
        pb = PromptBuilder()
        f = _make_source_file("src/node.cpp", FileType.CPP)
        plan = _make_plan()
        _, user = pb.build_transform_prompt(f, plan)
        assert "src/node.cpp" in user

    def test_user_contains_source_content(self):
        pb = PromptBuilder()
        content = "#include <ros/ros.h>\nint main() { return 0; }"
        f = _make_source_file(content=content)
        plan = _make_plan()
        _, user = pb.build_transform_prompt(f, plan)
        assert content in user


# ---------------------------------------------------------------------------
# Backend mode adaptation
# ---------------------------------------------------------------------------


class TestBackendMode:
    def test_api_mode_mentions_only_json(self):
        pb = PromptBuilder(backend_mode="api")
        f = _make_source_file()
        system, _ = pb.build_transform_prompt(f, _make_plan())
        assert "JSON" in system

    def test_cli_mode_mentions_markdown(self):
        pb = PromptBuilder(backend_mode="cli")
        f = _make_source_file()
        system, _ = pb.build_transform_prompt(f, _make_plan())
        assert "markdown" in system.lower() or "```json" in system


# ---------------------------------------------------------------------------
# Fix prompt stub
# ---------------------------------------------------------------------------


class TestBuildFixPrompt:
    def test_returns_two_strings(self):
        pb = PromptBuilder()
        f = _make_source_file()
        system, user = pb.build_fix_prompt(f, "broken output", "compile error")
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_user_contains_error_message(self):
        pb = PromptBuilder()
        f = _make_source_file()
        _, user = pb.build_fix_prompt(f, "broken", "compile error: undefined symbol")
        assert "compile error" in user

    def test_user_contains_original_content(self):
        pb = PromptBuilder()
        content = "#include <ros/ros.h>"
        f = _make_source_file(content=content)
        _, user = pb.build_fix_prompt(f, "broken output", "error")
        assert content in user
