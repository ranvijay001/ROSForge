"""Unit tests for ValidateFixLoopStage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from rosforge.models.config import RosForgeConfig, ValidationConfig
from rosforge.models.ir import FileType, PackageIR, PackageMetadata, SourceFile
from rosforge.models.result import BuildError, TransformedFile, ValidationResult
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.validate_fix_loop import ValidateFixLoopStage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(tmp_path: Path, auto_build: bool = False) -> PipelineContext:
    config = RosForgeConfig(validation=ValidationConfig(auto_build=auto_build))
    return PipelineContext(
        source_path=tmp_path / "src",
        output_path=tmp_path / "out",
        config=config,
    )


def _make_engine(fixed_content: str = "// fixed") -> MagicMock:
    engine = MagicMock()
    engine.fix.return_value = TransformedFile(
        source_path="src/node.cpp",
        target_path="src/node.cpp",
        original_content="// original",
        transformed_content=fixed_content,
        strategy_used="ai_driven",
    )
    return engine


def _success_result() -> ValidationResult:
    return ValidationResult(success=True, build_log="all good")


def _failure_result(msg: str = "error: missing symbol") -> ValidationResult:
    return ValidationResult(
        success=False,
        build_errors=[BuildError(file_path="src/node.cpp", message=msg, severity="error")],
        error_count=1,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidateFixLoopStageName:
    def test_name(self) -> None:
        assert ValidateFixLoopStage().name == "Validate+Fix"


class TestValidateFixLoopPassOnFirstValidate:
    def test_stops_after_first_validate_on_success(self, tmp_path: Path) -> None:
        """If the first validate passes, fix should never be called."""
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()

        with (
            patch("rosforge.pipeline.validate_fix_loop.ValidateStage") as MockValidate,
            patch("rosforge.pipeline.validate_fix_loop.FixStage") as MockFix,
        ):
            mock_validate_instance = MagicMock()
            mock_validate_instance.execute.side_effect = lambda c: (
                setattr(c, "validation_result", _success_result()) or c
            )
            MockValidate.return_value = mock_validate_instance

            mock_fix_instance = MagicMock()
            MockFix.return_value = mock_fix_instance

            result = ValidateFixLoopStage(max_attempts=3).execute(ctx)

        assert mock_validate_instance.execute.call_count == 1
        mock_fix_instance.execute.assert_not_called()
        assert result.validation_result is not None
        assert result.validation_result.success is True


class TestValidateFixLoopFixThenPass:
    def test_fix_once_then_validate_succeeds(self, tmp_path: Path) -> None:
        """First validate fails, fix runs, second validate succeeds."""
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()

        validate_results = [_failure_result(), _success_result()]
        validate_call_count = [0]

        def fake_validate_execute(c):
            result = validate_results[validate_call_count[0]]
            validate_call_count[0] += 1
            c.validation_result = result
            return c

        with (
            patch("rosforge.pipeline.validate_fix_loop.ValidateStage") as MockValidate,
            patch("rosforge.pipeline.validate_fix_loop.FixStage") as MockFix,
        ):
            mock_validate_instance = MagicMock()
            mock_validate_instance.execute.side_effect = fake_validate_execute
            MockValidate.return_value = mock_validate_instance

            mock_fix_instance = MagicMock()
            mock_fix_instance.execute.side_effect = lambda c: c
            MockFix.return_value = mock_fix_instance

            result = ValidateFixLoopStage(max_attempts=3).execute(ctx)

        assert mock_validate_instance.execute.call_count == 2
        assert mock_fix_instance.execute.call_count == 1
        assert result.validation_result.success is True


class TestValidateFixLoopExhaustsAttempts:
    def test_stops_after_max_attempts_exhausted(self, tmp_path: Path) -> None:
        """With max_attempts=2, validate runs 3 times, fix runs 2 times."""
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()

        def always_fail(c):
            c.validation_result = _failure_result()
            return c

        with (
            patch("rosforge.pipeline.validate_fix_loop.ValidateStage") as MockValidate,
            patch("rosforge.pipeline.validate_fix_loop.FixStage") as MockFix,
        ):
            mock_validate_instance = MagicMock()
            mock_validate_instance.execute.side_effect = always_fail
            MockValidate.return_value = mock_validate_instance

            mock_fix_instance = MagicMock()
            mock_fix_instance.execute.side_effect = lambda c: c
            MockFix.return_value = mock_fix_instance

            result = ValidateFixLoopStage(max_attempts=2).execute(ctx)

        # validate: attempt 0, 1, 2  ->  3 calls
        assert mock_validate_instance.execute.call_count == 3
        # fix: after attempt 0 and 1, but NOT after attempt 2  ->  2 calls
        assert mock_fix_instance.execute.call_count == 2
        assert result.validation_result.success is False

    def test_max_attempts_zero_means_validate_only(self, tmp_path: Path) -> None:
        """max_attempts=0 runs exactly one validate and no fix."""
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()

        def always_fail(c):
            c.validation_result = _failure_result()
            return c

        with (
            patch("rosforge.pipeline.validate_fix_loop.ValidateStage") as MockValidate,
            patch("rosforge.pipeline.validate_fix_loop.FixStage") as MockFix,
        ):
            mock_validate_instance = MagicMock()
            mock_validate_instance.execute.side_effect = always_fail
            MockValidate.return_value = mock_validate_instance

            mock_fix_instance = MagicMock()
            MockFix.return_value = mock_fix_instance

            result = ValidateFixLoopStage(max_attempts=0).execute(ctx)

        assert mock_validate_instance.execute.call_count == 1
        mock_fix_instance.execute.assert_not_called()
        assert result.validation_result.success is False


class TestValidateFixLoopDefaultMaxAttempts:
    def test_default_max_attempts_is_3(self, tmp_path: Path) -> None:
        """Default constructor uses max_attempts=3 (4 validate calls on total failure)."""
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()

        def always_fail(c):
            c.validation_result = _failure_result()
            return c

        with (
            patch("rosforge.pipeline.validate_fix_loop.ValidateStage") as MockValidate,
            patch("rosforge.pipeline.validate_fix_loop.FixStage") as MockFix,
        ):
            mock_validate_instance = MagicMock()
            mock_validate_instance.execute.side_effect = always_fail
            MockValidate.return_value = mock_validate_instance

            mock_fix_instance = MagicMock()
            mock_fix_instance.execute.side_effect = lambda c: c
            MockFix.return_value = mock_fix_instance

            ValidateFixLoopStage().execute(ctx)  # default

        assert mock_validate_instance.execute.call_count == 4  # 3 + 1
        assert mock_fix_instance.execute.call_count == 3
