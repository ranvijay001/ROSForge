"""Unit tests for PromptBuilder, ResponseParser, and ClaudeCLIEngine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.engine.response_parser import parse_analyze_response, parse_transform_response
from rosforge.models.config import EngineConfig
from rosforge.models.ir import FileType, PackageIR, PackageMetadata, SourceFile
from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy
from rosforge.models.result import SubprocessResult


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_ir() -> PackageIR:
    sf = SourceFile(
        relative_path="src/talker.cpp",
        file_type=FileType.CPP,
        content='#include <ros/ros.h>\nint main() { ros::init(); }',
        line_count=2,
    )
    return PackageIR(
        source_path=Path("/tmp/pkg"),
        metadata=PackageMetadata(name="test_pkg", version="0.1.0"),
        source_files=[sf],
        total_files=1,
        total_lines=2,
        cpp_files=1,
    )


@pytest.fixture()
def sample_plan() -> MigrationPlan:
    return MigrationPlan(
        package_name="test_pkg",
        actions=[
            TransformAction(
                source_path="src/talker.cpp",
                target_path="src/talker.cpp",
                strategy=TransformStrategy.AI_DRIVEN,
                confidence=0.8,
            )
        ],
    )


@pytest.fixture()
def engine_config() -> EngineConfig:
    return EngineConfig(name="claude", mode="cli", timeout_seconds=10)


# ── PromptBuilder tests ───────────────────────────────────────────────────────

class TestPromptBuilder:
    def test_estimate_tokens_empty(self):
        assert PromptBuilder.estimate_tokens("") == 0

    def test_estimate_tokens_basic(self):
        # 400 chars => ~100 tokens
        text = "a" * 400
        assert PromptBuilder.estimate_tokens(text) == 100

    def test_build_analyze_prompt_returns_tuple(self, sample_ir):
        builder = PromptBuilder()
        system, user = builder.build_analyze_prompt(sample_ir)
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_analyze_prompt_contains_package_name(self, sample_ir):
        builder = PromptBuilder()
        _, user = builder.build_analyze_prompt(sample_ir)
        assert "test_pkg" in user

    def test_analyze_prompt_system_has_knowledge(self, sample_ir):
        builder = PromptBuilder()
        system, _ = builder.build_analyze_prompt(sample_ir)
        assert "rclcpp" in system or "Knowledge" in system

    def test_build_transform_prompt_returns_tuple(self, sample_ir, sample_plan):
        builder = PromptBuilder()
        sf = sample_ir.source_files[0]
        system, user = builder.build_transform_prompt(sf, sample_plan)
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_transform_prompt_contains_file_content(self, sample_ir, sample_plan):
        builder = PromptBuilder()
        sf = sample_ir.source_files[0]
        _, user = builder.build_transform_prompt(sf, sample_plan)
        assert "ros/ros.h" in user or "talker.cpp" in user


# ── ResponseParser tests ──────────────────────────────────────────────────────

class TestResponseParser:
    VALID_TRANSFORM_JSON = """{
        "source_path": "src/talker.cpp",
        "target_path": "src/talker.cpp",
        "transformed_content": "#include <rclcpp/rclcpp.hpp>\\nint main() {}",
        "confidence": 0.85,
        "strategy_used": "ai_driven",
        "warnings": [],
        "changes": [{"description": "Updated include", "line_range": "1", "reason": "ROS2 API"}]
    }"""

    VALID_ANALYZE_JSON = """{
        "package_name": "test_pkg",
        "target_ros2_distro": "humble",
        "overall_confidence": 0.8,
        "summary": "2 files to migrate",
        "warnings": [],
        "actions": [
            {
                "source_path": "src/talker.cpp",
                "target_path": "src/talker.cpp",
                "strategy": "ai_driven",
                "description": "C++ node needs AI transform",
                "estimated_complexity": 3,
                "confidence": 0.75
            }
        ]
    }"""

    def test_parse_transform_valid_json(self):
        result = parse_transform_response(self.VALID_TRANSFORM_JSON)
        assert result.source_path == "src/talker.cpp"
        assert result.confidence == pytest.approx(0.85)
        assert len(result.changes) == 1

    def test_parse_transform_json_fence(self):
        fenced = f"Here is the result:\n```json\n{self.VALID_TRANSFORM_JSON}\n```"
        result = parse_transform_response(fenced)
        assert result.source_path == "src/talker.cpp"

    def test_parse_transform_generic_fence(self):
        fenced = f"```\n{self.VALID_TRANSFORM_JSON}\n```"
        result = parse_transform_response(fenced)
        assert result.source_path == "src/talker.cpp"

    def test_parse_transform_failure(self):
        result = parse_transform_response("not json at all")
        assert "parse_failure" in result.warnings[0]
        assert result.transformed_content == "not json at all"

    def test_parse_analyze_valid_json(self):
        result = parse_analyze_response(self.VALID_ANALYZE_JSON)
        assert result.package_name == "test_pkg"
        assert result.overall_confidence == pytest.approx(0.8)
        assert len(result.actions) == 1
        assert result.actions[0].strategy == TransformStrategy.AI_DRIVEN

    def test_parse_analyze_failure(self):
        result = parse_analyze_response("garbage text")
        assert any("parse_failure" in w for w in result.warnings)


# ── ClaudeCLIEngine tests (mocked subprocess) ─────────────────────────────────

class TestClaudeCLIEngine:
    def test_health_check_success(self, engine_config):
        from rosforge.engine.claude.cli_backend import ClaudeCLIEngine

        mock_result = SubprocessResult(status="success", exit_code=0, parsed_json={})
        with patch("rosforge.engine.claude.cli_backend.run_command", return_value=mock_result):
            engine = ClaudeCLIEngine(engine_config)
            assert engine.health_check() is True

    def test_health_check_failure(self, engine_config):
        from rosforge.engine.claude.cli_backend import ClaudeCLIEngine

        mock_result = SubprocessResult(status="error", exit_code=1, error_message="not found")
        with patch("rosforge.engine.claude.cli_backend.run_command", return_value=mock_result):
            engine = ClaudeCLIEngine(engine_config)
            assert engine.health_check() is False

    def test_analyze_calls_subprocess(self, engine_config, sample_ir):
        from rosforge.engine.claude.cli_backend import ClaudeCLIEngine

        valid_response = '{"package_name":"test_pkg","target_ros2_distro":"humble","overall_confidence":0.8,"summary":"ok","warnings":[],"actions":[]}'
        mock_result = SubprocessResult(
            status="success", exit_code=0,
            raw_stdout=valid_response,
            parsed_json={"package_name": "test_pkg"},
        )
        with patch("rosforge.engine.claude.cli_backend.run_command", return_value=mock_result):
            engine = ClaudeCLIEngine(engine_config)
            plan = engine.analyze(sample_ir)
            assert plan.package_name == "test_pkg"

    def test_transform_calls_subprocess(self, engine_config, sample_ir, sample_plan):
        from rosforge.engine.claude.cli_backend import ClaudeCLIEngine

        valid_response = '{"source_path":"src/talker.cpp","target_path":"src/talker.cpp","transformed_content":"// ros2","confidence":0.9,"strategy_used":"ai_driven","warnings":[],"changes":[]}'
        mock_result = SubprocessResult(
            status="success", exit_code=0,
            raw_stdout=valid_response,
            parsed_json={"source_path": "src/talker.cpp"},
        )
        sf = sample_ir.source_files[0]
        with patch("rosforge.engine.claude.cli_backend.run_command", return_value=mock_result):
            engine = ClaudeCLIEngine(engine_config)
            result = engine.transform(sf, sample_plan)
            assert result.source_path == "src/talker.cpp"
            assert result.original_content == sf.content
