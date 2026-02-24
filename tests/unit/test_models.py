"""Unit tests for all Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from rosforge.models.config import (
    EngineConfig,
    MigrationConfig,
    RosForgeConfig,
    TelemetryConfig,
    ValidationConfig,
)
from rosforge.models.ir import (
    Dependency,
    DependencyType,
    FileType,
    PackageIR,
    PackageMetadata,
    ROSAPIUsage,
    SourceFile,
)
from rosforge.models.plan import (
    CostEstimate,
    MigrationPlan,
    TransformAction,
    TransformStrategy,
)
from rosforge.models.result import (
    BuildError,
    ChangeEntry,
    SubprocessResult,
    TransformedFile,
    ValidationResult,
)
from rosforge.models.report import (
    AnalysisReport,
    FileChangeRecord,
    MigrationReport,
)
from rosforge.telemetry.events import (
    AnalyzeRunEvent,
    BuildResultEvent,
    MigrationEndEvent,
    MigrationStartEvent,
    TelemetryEvent,
)


class TestConfigModels:
    def test_engine_config_defaults(self):
        cfg = EngineConfig()
        assert cfg.name == "claude"
        assert cfg.mode == "cli"
        assert cfg.timeout_seconds == 300

    def test_telemetry_config_none_by_default(self):
        cfg = TelemetryConfig()
        assert cfg.enabled is None
        assert cfg.local_log is True

    def test_rosforge_config_roundtrip(self):
        cfg = RosForgeConfig()
        data = cfg.model_dump()
        restored = RosForgeConfig.model_validate(data)
        assert restored.engine.name == cfg.engine.name
        assert restored.telemetry.enabled == cfg.telemetry.enabled

    def test_config_dir_properties(self):
        cfg = RosForgeConfig()
        assert cfg.config_dir.name == ".rosforge"
        assert cfg.config_path.name == "config.toml"
        assert cfg.log_dir.name == "logs"


class TestIRModels:
    def test_source_file_defaults(self):
        sf = SourceFile(relative_path="src/foo.cpp", file_type=FileType.CPP)
        assert sf.content == ""
        assert sf.line_count == 0
        assert sf.api_usages == []

    def test_package_ir_get_files_by_type(self):
        from pathlib import Path
        sf_cpp = SourceFile(relative_path="src/a.cpp", file_type=FileType.CPP)
        sf_py = SourceFile(relative_path="scripts/b.py", file_type=FileType.PYTHON)
        ir = PackageIR(source_path=Path("/tmp/pkg"), source_files=[sf_cpp, sf_py])
        assert ir.get_files_by_type(FileType.CPP) == [sf_cpp]
        assert ir.get_files_by_type(FileType.PYTHON) == [sf_py]
        assert ir.get_files_by_type(FileType.CMAKE) == []

    def test_dependency_model(self):
        dep = Dependency(name="roscpp", dep_type=DependencyType.BUILD)
        assert dep.name == "roscpp"
        assert dep.dep_type == DependencyType.BUILD

    def test_ros_api_usage(self):
        usage = ROSAPIUsage(api_name="ros::NodeHandle", file_path="src/a.cpp", line_number=10)
        assert usage.api_name == "ros::NodeHandle"


class TestPlanModels:
    def test_migration_plan_counts(self):
        actions = [
            TransformAction(
                source_path="a.cpp", target_path="a.cpp",
                strategy=TransformStrategy.AI_DRIVEN, confidence=0.8
            ),
            TransformAction(
                source_path="package.xml", target_path="package.xml",
                strategy=TransformStrategy.RULE_BASED, confidence=0.95
            ),
        ]
        plan = MigrationPlan(actions=actions)
        assert plan.ai_driven_count == 1
        assert plan.rule_based_count == 1

    def test_cost_estimate_defaults(self):
        est = CostEstimate()
        assert est.estimated_cost_usd == 0.0
        assert est.engine_name == ""


class TestResultModels:
    def test_transformed_file_has_changes(self):
        tf = TransformedFile(
            source_path="a.cpp", target_path="a.cpp",
            original_content="old", transformed_content="new"
        )
        assert tf.has_changes is True

    def test_transformed_file_no_changes(self):
        tf = TransformedFile(
            source_path="a.cpp", target_path="a.cpp",
            original_content="same", transformed_content="same"
        )
        assert tf.has_changes is False

    def test_subprocess_result_ok(self):
        sr = SubprocessResult(status="success", parsed_json={"a": 1}, exit_code=0)
        assert sr.ok is True

    def test_subprocess_result_not_ok_on_parse_failure(self):
        sr = SubprocessResult(status="parse_failure", exit_code=0)
        assert sr.ok is False


class TestTelemetryEvents:
    def test_migration_start_event(self):
        ev = MigrationStartEvent(engine="claude-cli", package_file_count=5, total_lines=200)
        assert ev.event_type == "migration_start"
        assert ev.engine == "claude-cli"
        assert isinstance(ev.timestamp, datetime)

    def test_migration_end_event(self):
        ev = MigrationEndEvent(duration_s=12.5, success=True, files_transformed=3, confidence_avg=0.85)
        assert ev.event_type == "migration_end"
        assert ev.success is True

    def test_build_result_event(self):
        ev = BuildResultEvent(passed=True, error_count=0)
        assert ev.event_type == "build_result"

    def test_analyze_run_event(self):
        ev = AnalyzeRunEvent(dependency_count=4)
        assert ev.event_type == "analyze_run"
        assert ev.dependency_count == 4

    def test_event_serializes_to_json(self):
        import json
        ev = MigrationStartEvent(engine="claude-cli", package_file_count=2, total_lines=100)
        data = json.loads(ev.model_dump_json())
        assert data["event_type"] == "migration_start"
        assert "timestamp" in data
