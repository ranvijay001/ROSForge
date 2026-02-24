"""Unit tests for InteractiveReviewStage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.models.ir import FileType, PackageIR, PackageMetadata, SourceFile
from rosforge.models.result import TransformedFile
from rosforge.pipeline.interactive import InteractiveReviewStage
from rosforge.pipeline.runner import PipelineContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source_file(relative_path: str, content: str) -> SourceFile:
    return SourceFile(
        relative_path=relative_path,
        file_type=FileType.CPP,
        content=content,
    )


def _make_package_ir(source_files: list[SourceFile], source_path: Path) -> PackageIR:
    return PackageIR(
        source_path=source_path,
        metadata=PackageMetadata(name="test_pkg", version="1.0.0"),
        source_files=source_files,
    )


def _make_transformed(
    source_path: str = "src/node.cpp",
    original: str = "// original",
    transformed: str = "// transformed",
) -> TransformedFile:
    return TransformedFile(
        source_path=source_path,
        target_path=source_path,
        original_content=original,
        transformed_content=transformed,
        strategy_used="rule_based",
    )


def _make_ctx(tmp_path: Path, transformed_files: list[TransformedFile]) -> PipelineContext:
    source_files = [
        _make_source_file(tf.source_path, tf.original_content) for tf in transformed_files
    ]
    config = RosForgeConfig()
    ctx = PipelineContext(
        source_path=tmp_path / "src",
        output_path=tmp_path / "out",
        config=config,
    )
    ctx.package_ir = _make_package_ir(source_files, tmp_path / "src")
    ctx.transformed_files = transformed_files
    return ctx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_accept_all(tmp_path: Path) -> None:
    """Pressing 'A' for every file keeps all transformed content unchanged."""
    files = [
        _make_transformed("src/a.cpp", "// orig_a", "// new_a"),
        _make_transformed("src/b.cpp", "// orig_b", "// new_b"),
    ]
    ctx = _make_ctx(tmp_path, files)

    with patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="a"):
        ctx = InteractiveReviewStage().execute(ctx)

    assert len(ctx.transformed_files) == 2
    for tf in ctx.transformed_files:
        assert tf.user_reviewed is True
        assert tf.user_action == "accept"
    assert ctx.transformed_files[0].transformed_content == "// new_a"
    assert ctx.transformed_files[1].transformed_content == "// new_b"


def test_skip_file(tmp_path: Path) -> None:
    """Pressing 'S' reverts the file to its original content."""
    files = [
        _make_transformed("src/node.cpp", "// original", "// transformed"),
    ]
    ctx = _make_ctx(tmp_path, files)

    with patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="s"):
        ctx = InteractiveReviewStage().execute(ctx)

    assert len(ctx.transformed_files) == 1
    tf = ctx.transformed_files[0]
    assert tf.user_reviewed is True
    assert tf.user_action == "skip"
    # Content must be reverted to original
    assert tf.transformed_content == "// original"


def test_quit_early(tmp_path: Path) -> None:
    """Pressing 'Q' on the first file accepts it and all remaining without prompting."""
    files = [
        _make_transformed("src/a.cpp", "// orig_a", "// new_a"),
        _make_transformed("src/b.cpp", "// orig_b", "// new_b"),
        _make_transformed("src/c.cpp", "// orig_c", "// new_c"),
    ]
    ctx = _make_ctx(tmp_path, files)

    # 'q' on first prompt — remaining files should be accepted automatically
    with patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", return_value="q"):
        ctx = InteractiveReviewStage().execute(ctx)

    assert len(ctx.transformed_files) == 3
    for tf in ctx.transformed_files:
        assert tf.user_reviewed is True
        assert tf.user_action == "accept"
    # Transformed content must be preserved (not reverted)
    assert ctx.transformed_files[0].transformed_content == "// new_a"
    assert ctx.transformed_files[1].transformed_content == "// new_b"
    assert ctx.transformed_files[2].transformed_content == "// new_c"


def test_no_tty_skips(tmp_path: Path) -> None:
    """When stdin is not a TTY the stage is a no-op — files unchanged."""
    files = [
        _make_transformed("src/node.cpp", "// original", "// transformed"),
    ]
    ctx = _make_ctx(tmp_path, files)
    original_files = list(ctx.transformed_files)

    with patch("sys.stdin.isatty", return_value=False):
        # Should not raise, and should not prompt
        with patch("builtins.input", side_effect=AssertionError("input() must not be called")):
            ctx = InteractiveReviewStage().execute(ctx)

    # Files are unchanged (no user_action set)
    assert len(ctx.transformed_files) == 1
    assert ctx.transformed_files[0].transformed_content == "// transformed"
    assert ctx.transformed_files[0].user_action == ""


def test_empty_transforms(tmp_path: Path) -> None:
    """When there are no transformed files the stage is a no-op."""
    config = RosForgeConfig()
    ctx = PipelineContext(
        source_path=tmp_path / "src",
        output_path=tmp_path / "out",
        config=config,
    )
    ctx.transformed_files = []

    with patch("sys.stdin.isatty", return_value=True), \
         patch("builtins.input", side_effect=AssertionError("input() must not be called")):
        ctx = InteractiveReviewStage().execute(ctx)

    assert ctx.transformed_files == []
