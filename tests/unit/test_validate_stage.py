"""Unit tests for ValidateStage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rosforge.models.config import RosForgeConfig, ValidationConfig
from rosforge.models.result import SubprocessResult, ValidationResult
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.validate import ValidateStage, _parse_build_errors


class TestParseBuildErrors:
    def test_parses_cpp_error(self) -> None:
        log = "src/main.cpp:10:5: error: 'ros::init' was not declared"
        errors, err_count, warn_count = _parse_build_errors(log)
        assert err_count >= 1
        assert any("main.cpp" in e.file_path for e in errors)

    def test_parses_cpp_warning(self) -> None:
        log = "src/node.cpp:25:3: warning: unused variable 'x'"
        errors, err_count, warn_count = _parse_build_errors(log)
        assert warn_count >= 1
        assert any(e.severity == "warning" for e in errors)

    def test_parses_generic_error(self) -> None:
        log = "CMake Error: could not find package roscpp"
        errors, err_count, warn_count = _parse_build_errors(log)
        assert err_count >= 1

    def test_empty_log(self) -> None:
        errors, err_count, warn_count = _parse_build_errors("")
        assert errors == []
        assert err_count == 0
        assert warn_count == 0

    def test_clean_build(self) -> None:
        log = "Starting >>> my_package\nFinished <<< my_package [2.5s]\nSummary: 1 package finished"
        errors, err_count, warn_count = _parse_build_errors(log)
        assert err_count == 0


class TestValidateStage:
    def _make_ctx(self, tmp_path: Path, **validation_kwargs) -> PipelineContext:
        config = RosForgeConfig(
            validation=ValidationConfig(**validation_kwargs)
        )
        return PipelineContext(
            source_path=tmp_path / "src",
            output_path=tmp_path / "out",
            config=config,
        )

    def test_skips_when_auto_build_false(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path, auto_build=False)
        stage = ValidateStage()
        result_ctx = stage.execute(ctx)
        assert result_ctx.validation_result is not None
        assert result_ctx.validation_result.success is True
        assert "skipped" in result_ctx.validation_result.build_log.lower()

    def test_fails_gracefully_when_colcon_missing(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path, auto_build=True)
        stage = ValidateStage()
        with patch("shutil.which", return_value=None):
            result_ctx = stage.execute(ctx)
        assert result_ctx.validation_result is not None
        assert result_ctx.validation_result.success is False
        assert "colcon" in result_ctx.validation_result.build_log.lower()

    def test_successful_build(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path, auto_build=True, rosdep_install=False)
        stage = ValidateStage()

        mock_result = SubprocessResult(
            status="success",
            raw_stdout="Summary: 1 package finished",
            raw_stderr="",
            exit_code=0,
            parsed_json={"status": "ok"},
        )

        with patch("shutil.which", return_value="/usr/bin/colcon"), \
             patch("rosforge.pipeline.validate.run_command", return_value=mock_result):
            result_ctx = stage.execute(ctx)

        assert result_ctx.validation_result is not None
        assert result_ctx.validation_result.success is True
        assert result_ctx.validation_result.error_count == 0

    def test_failed_build_with_errors(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path, auto_build=True, rosdep_install=False)
        stage = ValidateStage()

        mock_result = SubprocessResult(
            status="error",
            raw_stdout="",
            raw_stderr="src/node.cpp:5:1: error: 'ros' was not declared",
            exit_code=1,
            error_message="Command exited with code 1",
        )

        with patch("shutil.which", return_value="/usr/bin/colcon"), \
             patch("rosforge.pipeline.validate.run_command", return_value=mock_result):
            result_ctx = stage.execute(ctx)

        assert result_ctx.validation_result is not None
        assert result_ctx.validation_result.success is False

    def test_stage_name(self) -> None:
        assert ValidateStage().name == "Validate"

    def test_rosdep_called_when_enabled(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path, auto_build=True, rosdep_install=True)
        stage = ValidateStage()

        mock_result = SubprocessResult(
            status="success",
            raw_stdout="",
            raw_stderr="",
            exit_code=0,
            parsed_json={},
        )

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return mock_result

        with patch("shutil.which", return_value="/usr/bin/colcon"), \
             patch("rosforge.pipeline.validate.run_command", side_effect=fake_run):
            result_ctx = stage.execute(ctx)

        # rosdep call should have been made (it's best-effort, so we check it tried)
        rosdep_calls = [c for c in calls if c and "rosdep" in c[0]]
        assert len(rosdep_calls) >= 1
