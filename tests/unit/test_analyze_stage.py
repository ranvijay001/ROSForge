"""Tests for the enhanced AnalyzeStage."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.models.ir import (
    Dependency,
    DependencyType,
    FileType,
    PackageIR,
    PackageMetadata,
    ROSAPIUsage,
    SourceFile,
)
from rosforge.models.plan import Confidence
from rosforge.pipeline.analyze import (
    AnalyzeStage,
    _classify_complexity,
    _compute_risk_score,
    _resolve_dependency,
    _transform_strategy,
)
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_source_file(
    path: str = "src/node.cpp",
    file_type: FileType = FileType.CPP,
    line_count: int = 100,
    api_count: int = 0,
) -> SourceFile:
    usages = [
        ROSAPIUsage(api_name=f"ros::init{i}", file_path=path, line_number=i)
        for i in range(api_count)
    ]
    return SourceFile(
        relative_path=path,
        file_type=file_type,
        content="",
        line_count=line_count,
        api_usages=usages,
    )


def _make_ir(
    name: str = "test_pkg",
    source_files: list[SourceFile] | None = None,
    dependencies: list[Dependency] | None = None,
) -> PackageIR:
    files = source_files or []
    deps = dependencies or []
    return PackageIR(
        source_path=Path("/tmp/test_pkg"),
        metadata=PackageMetadata(name=name, version="1.0.0"),
        source_files=files,
        dependencies=deps,
        api_usages=[u for f in files for u in f.api_usages],
        total_files=len(files),
        total_lines=sum(f.line_count for f in files),
        cpp_files=sum(1 for f in files if f.file_type == FileType.CPP),
        python_files=sum(1 for f in files if f.file_type == FileType.PYTHON),
        launch_files=sum(1 for f in files if f.file_type == FileType.LAUNCH_XML),
        msg_srv_files=sum(1 for f in files if f.file_type in (FileType.MSG, FileType.SRV)),
    )


def _make_ctx(ir: PackageIR | None = None) -> PipelineContext:
    config = RosForgeConfig()
    ctx = PipelineContext(
        source_path=Path("/tmp/test_pkg"),
        output_path=Path("/tmp/test_pkg_out"),
        config=config,
    )
    ctx.package_ir = ir
    return ctx


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestClassifyComplexity:
    def test_simple_file_is_complexity_1(self):
        f = _make_source_file(line_count=20, api_count=1)
        assert _classify_complexity(f) == 1

    def test_medium_file_is_complexity_2(self):
        f = _make_source_file(line_count=100, api_count=3)
        assert _classify_complexity(f) == 2

    def test_large_file_is_complexity_3(self):
        f = _make_source_file(line_count=300, api_count=7)
        assert _classify_complexity(f) == 3

    def test_very_large_file_is_complexity_4(self):
        f = _make_source_file(line_count=700, api_count=15)
        assert _classify_complexity(f) == 4

    def test_huge_file_is_complexity_5(self):
        f = _make_source_file(line_count=2000, api_count=30)
        assert _classify_complexity(f) == 5


class TestTransformStrategy:
    def test_cmake_is_rule_based(self):
        f = _make_source_file(file_type=FileType.CMAKE)
        assert _transform_strategy(f) == "rule_based"

    def test_package_xml_is_rule_based(self):
        f = _make_source_file(file_type=FileType.PACKAGE_XML)
        assert _transform_strategy(f) == "rule_based"

    def test_msg_is_rule_based(self):
        f = _make_source_file(file_type=FileType.MSG)
        assert _transform_strategy(f) == "rule_based"

    def test_cpp_without_apis_is_rule_based(self):
        f = _make_source_file(file_type=FileType.CPP, api_count=0)
        assert _transform_strategy(f) == "rule_based"

    def test_cpp_with_apis_is_ai_driven(self):
        f = _make_source_file(file_type=FileType.CPP, api_count=3)
        assert _transform_strategy(f) == "ai_driven"

    def test_python_with_apis_is_ai_driven(self):
        f = _make_source_file(file_type=FileType.PYTHON, api_count=2)
        assert _transform_strategy(f) == "ai_driven"

    def test_launch_xml_is_ai_driven(self):
        f = _make_source_file(file_type=FileType.LAUNCH_XML)
        assert _transform_strategy(f) == "ai_driven"


class TestResolveDependency:
    def test_known_ros1_dep_maps_correctly(self):
        # roscpp is a well-known ROS1 dep
        from rosforge.knowledge import ROS1_TO_ROS2_PACKAGES

        if "roscpp" in ROS1_TO_ROS2_PACKAGES:
            report = _resolve_dependency("roscpp")
            assert report.available_in_ros2
            assert report.ros2_equivalent == ROS1_TO_ROS2_PACKAGES["roscpp"]

    def test_rclcpp_already_ros2(self):
        report = _resolve_dependency("rclcpp")
        assert report.available_in_ros2
        assert report.ros2_equivalent == "rclcpp"

    def test_std_msgs_passthrough(self):
        report = _resolve_dependency("std_msgs")
        assert report.available_in_ros2

    def test_unknown_dep_flagged(self):
        report = _resolve_dependency("some_ros1_only_package_xyz_123")
        assert not report.available_in_ros2
        assert report.ros2_equivalent == ""


# ---------------------------------------------------------------------------
# Integration tests for AnalyzeStage
# ---------------------------------------------------------------------------


class TestAnalyzeStage:
    def test_fails_without_ir(self):
        ctx = _make_ctx(ir=None)
        stage = AnalyzeStage()
        ctx = stage.execute(ctx)
        assert ctx.fatal_errors
        assert "Ingest" in ctx.fatal_errors[0].message

    def test_produces_analysis_report(self):
        files = [
            _make_source_file("src/node.cpp", FileType.CPP, 100, 3),
            _make_source_file("CMakeLists.txt", FileType.CMAKE, 50, 0),
        ]
        deps = [Dependency(name="roscpp", dep_type=DependencyType.BUILD)]
        ir = _make_ir(source_files=files, dependencies=deps)
        ctx = _make_ctx(ir=ir)

        stage = AnalyzeStage()
        ctx = stage.execute(ctx)

        assert not ctx.fatal_errors
        assert ctx.analysis_report
        import json

        data = json.loads(ctx.analysis_report)
        assert data["package_name"] == "test_pkg"
        assert data["total_files"] == 2
        assert data["risk_score"] >= 0.0
        assert data["risk_score"] <= 1.0

    def test_cost_estimate_set(self):
        files = [_make_source_file("src/node.cpp", FileType.CPP, 200, 5)]
        ir = _make_ir(source_files=files)
        ctx = _make_ctx(ir=ir)

        AnalyzeStage().execute(ctx)

        assert ctx.cost_estimate is not None
        assert ctx.cost_estimate.estimated_api_calls >= 1

    def test_launch_file_warning(self):
        files = [
            _make_source_file("launch/start.launch", FileType.LAUNCH_XML, 30, 0),
        ]
        ir = _make_ir(source_files=files)
        ir = ir.model_copy(update={"launch_files": 1})
        ctx = _make_ctx(ir=ir)

        AnalyzeStage().execute(ctx)

        import json

        data = json.loads(ctx.analysis_report)
        assert any("launch" in w.lower() for w in data["warnings"])

    def test_high_risk_package_has_low_confidence(self):
        # Many files with many API usages -> high risk -> low confidence
        files = [_make_source_file(f"src/node{i}.cpp", FileType.CPP, 1000, 25) for i in range(5)]
        deps = [
            Dependency(name=f"missing_dep_{i}", dep_type=DependencyType.BUILD) for i in range(5)
        ]
        ir = _make_ir(source_files=files, dependencies=deps)
        ctx = _make_ctx(ir=ir)

        AnalyzeStage().execute(ctx)

        import json

        data = json.loads(ctx.analysis_report)
        assert data["confidence"] in ("low", "medium")

    def test_simple_package_has_high_confidence(self):
        files = [_make_source_file("CMakeLists.txt", FileType.CMAKE, 20, 0)]
        ir = _make_ir(source_files=files)
        ctx = _make_ctx(ir=ir)

        AnalyzeStage().execute(ctx)

        import json

        data = json.loads(ctx.analysis_report)
        assert data["confidence"] == "high"
