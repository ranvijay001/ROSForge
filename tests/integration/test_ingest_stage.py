"""Integration tests for the IngestStage using real fixture packages."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.models.ir import FileType
from rosforge.pipeline.ingest import IngestStage
from rosforge.pipeline.runner import PipelineContext

FIXTURES = Path(__file__).parent.parent / "fixtures"
ROS1_MINIMAL = FIXTURES / "ros1_minimal"
ROS1_PYTHON = FIXTURES / "ros1_python"


def _make_ctx(source: Path, tmp_path: Path) -> PipelineContext:
    return PipelineContext(
        source_path=source,
        output_path=tmp_path / "output",
        config=RosForgeConfig(),
    )


class TestIngestStageMinimal:
    def test_no_errors_on_valid_package(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert not ctx.fatal_errors, ctx.fatal_errors

    def test_package_ir_populated(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert ctx.package_ir is not None

    def test_package_name_detected(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert ctx.package_ir.metadata.name == "ros1_minimal"

    def test_package_version_detected(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert ctx.package_ir.metadata.version == "0.1.0"

    def test_cmake_file_found(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        types = {f.file_type for f in ctx.package_ir.source_files}
        assert FileType.CMAKE in types

    def test_cpp_file_found(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        types = {f.file_type for f in ctx.package_ir.source_files}
        assert FileType.CPP in types

    def test_dependencies_detected(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        dep_names = {d.name for d in ctx.package_ir.dependencies}
        assert "roscpp" in dep_names
        assert "std_msgs" in dep_names

    def test_total_files_gt_zero(self, tmp_path):
        ctx = _make_ctx(ROS1_MINIMAL, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert ctx.package_ir.total_files > 0


class TestIngestStagePython:
    def test_no_errors_on_python_package(self, tmp_path):
        ctx = _make_ctx(ROS1_PYTHON, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert not ctx.fatal_errors, ctx.fatal_errors

    def test_package_name_ros1_python(self, tmp_path):
        ctx = _make_ctx(ROS1_PYTHON, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert ctx.package_ir.metadata.name == "ros1_python"

    def test_python_file_found(self, tmp_path):
        ctx = _make_ctx(ROS1_PYTHON, tmp_path)
        ctx = IngestStage().execute(ctx)
        types = {f.file_type for f in ctx.package_ir.source_files}
        assert FileType.PYTHON in types

    def test_rospy_dependency_detected(self, tmp_path):
        ctx = _make_ctx(ROS1_PYTHON, tmp_path)
        ctx = IngestStage().execute(ctx)
        dep_names = {d.name for d in ctx.package_ir.dependencies}
        assert "rospy" in dep_names


class TestIngestStageErrors:
    def test_missing_package_xml_raises_error(self, tmp_path):
        # Create a directory with no package.xml
        empty_pkg = tmp_path / "empty_pkg"
        empty_pkg.mkdir()
        (empty_pkg / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.0.2)\n")

        ctx = _make_ctx(empty_pkg, tmp_path)
        ctx = IngestStage().execute(ctx)
        assert ctx.fatal_errors
        assert "package.xml" in ctx.fatal_errors[0].message
