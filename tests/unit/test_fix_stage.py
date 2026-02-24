"""Unit tests for FixStage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.models.ir import FileType, PackageIR, PackageMetadata, SourceFile
from rosforge.models.result import BuildError, TransformedFile, ValidationResult
from rosforge.pipeline.fix import FixStage
from rosforge.pipeline.runner import PipelineContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(tmp_path: Path) -> PipelineContext:
    config = RosForgeConfig()
    return PipelineContext(
        source_path=tmp_path / "src",
        output_path=tmp_path / "out",
        config=config,
    )


def _make_source_file(
    relative_path: str = "src/node.cpp", content: str = "// original"
) -> SourceFile:
    return SourceFile(
        relative_path=relative_path,
        file_type=FileType.CPP,
        content=content,
    )


def _make_transformed_file(
    source_path: str = "src/node.cpp",
    target_path: str = "src/node.cpp",
    transformed_content: str = "// transformed",
    original_content: str = "// original",
) -> TransformedFile:
    return TransformedFile(
        source_path=source_path,
        target_path=target_path,
        original_content=original_content,
        transformed_content=transformed_content,
        strategy_used="ai_driven",
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


def _make_ir(source_file: SourceFile | None = None) -> PackageIR:
    sf = source_file or _make_source_file()
    return PackageIR(
        source_path=Path("/tmp/pkg"),
        metadata=PackageMetadata(name="test_pkg", version="1.0.0"),
        source_files=[sf],
    )


def _make_validation_result(errors: list[BuildError], success: bool = False) -> ValidationResult:
    return ValidationResult(
        success=success,
        build_errors=errors,
        error_count=sum(1 for e in errors if e.severity == "error"),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFixStageRequirements:
    def test_fails_without_engine(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.validation_result = _make_validation_result([])
        result = FixStage().execute(ctx)
        assert result.fatal_errors
        assert "engine" in result.fatal_errors[0].message.lower()

    def test_fails_without_validation_result(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()
        result = FixStage().execute(ctx)
        assert result.fatal_errors
        assert "validation" in result.fatal_errors[0].message.lower()

    def test_name_is_fix(self) -> None:
        assert FixStage().name == "Fix"


class TestFixStageFileMatching:
    def test_fixes_file_matched_by_target_path(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine("// fixed content")
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file(target_path="src/node.cpp")]
        ctx.validation_result = _make_validation_result(
            [
                BuildError(
                    file_path="src/node.cpp",
                    line_number=5,
                    message="undefined symbol",
                    severity="error",
                ),
            ]
        )

        result = FixStage().execute(ctx)

        assert result.transformed_files[0].transformed_content == "// fixed content"

    def test_fixes_file_matched_by_basename(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine("// fixed")
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file(target_path="src/node.cpp")]
        # Compiler error contains full build-tree path
        ctx.validation_result = _make_validation_result(
            [
                BuildError(
                    file_path="/workspace/build/my_pkg/CMakeFiles/node.cpp",
                    line_number=10,
                    message="unknown type",
                    severity="error",
                ),
            ]
        )

        result = FixStage().execute(ctx)

        assert result.transformed_files[0].transformed_content == "// fixed"

    def test_fixes_first_file_when_error_has_no_path(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine("// fixed fallback")
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file(target_path="src/node.cpp")]
        ctx.validation_result = _make_validation_result(
            [
                BuildError(
                    file_path="",
                    line_number=0,
                    message="CMake error: missing package",
                    severity="error",
                ),
            ]
        )

        result = FixStage().execute(ctx)

        assert result.transformed_files[0].transformed_content == "// fixed fallback"

    def test_skips_warnings(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file(target_path="src/node.cpp")]
        ctx.validation_result = _make_validation_result(
            [
                BuildError(
                    file_path="src/node.cpp",
                    line_number=3,
                    message="unused var",
                    severity="warning",
                ),
            ]
        )
        original_content = ctx.transformed_files[0].transformed_content

        result = FixStage().execute(ctx)

        # engine.fix should not have been called for warnings only
        ctx.engine.fix.assert_not_called()
        assert result.transformed_files[0].transformed_content == original_content


class TestFixStageFileWriting:
    def test_writes_fixed_file_to_output_path(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine("// fixed written")
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file(target_path="src/node.cpp")]
        ctx.validation_result = _make_validation_result(
            [
                BuildError(
                    file_path="src/node.cpp", line_number=1, message="error here", severity="error"
                ),
            ]
        )

        FixStage().execute(ctx)

        out_file = tmp_path / "out" / "src" / "node.cpp"
        assert out_file.exists()
        assert out_file.read_text() == "// fixed written"


class TestFixStageAttemptTracking:
    def test_increments_fix_attempts(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file()]
        ctx.validation_result = _make_validation_result(
            [
                BuildError(file_path="src/node.cpp", message="err", severity="error"),
            ]
        )

        assert ctx.fix_attempts == 0
        FixStage().execute(ctx)
        assert ctx.fix_attempts == 1
        FixStage().execute(ctx)
        assert ctx.fix_attempts == 2

    def test_increments_even_with_no_errors(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        ctx.engine = _make_engine()
        ctx.package_ir = _make_ir()
        ctx.transformed_files = []
        ctx.validation_result = _make_validation_result([])

        FixStage().execute(ctx)
        assert ctx.fix_attempts == 1


class TestFixStageEngineError:
    def test_engine_exception_is_recoverable(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        engine = MagicMock()
        engine.fix.side_effect = RuntimeError("backend unavailable")
        ctx.engine = engine
        ctx.package_ir = _make_ir()
        ctx.transformed_files = [_make_transformed_file()]
        ctx.validation_result = _make_validation_result(
            [
                BuildError(file_path="src/node.cpp", message="err", severity="error"),
            ]
        )
        original_content = ctx.transformed_files[0].transformed_content

        result = FixStage().execute(ctx)

        # Should record a recoverable error, not crash
        assert any(e.recoverable for e in result.errors)
        # Content unchanged on failure
        assert result.transformed_files[0].transformed_content == original_content
