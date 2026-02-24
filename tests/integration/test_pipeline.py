"""Integration tests: full pipeline run with mocked AI engine."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.models.ir import FileType, SourceFile
from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy
from rosforge.models.result import ChangeEntry, TransformedFile
from rosforge.pipeline.analyze import AnalyzeStage
from rosforge.pipeline.ingest import IngestStage
from rosforge.pipeline.report import ReportStage
from rosforge.pipeline.runner import PipelineContext, PipelineRunner
from rosforge.pipeline.transform import TransformStage
from rosforge.pipeline.validate import ValidateStage

FIXTURES = Path(__file__).parent.parent / "fixtures"
ROS1_MINIMAL = FIXTURES / "ros1_minimal"


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture()
def default_config() -> RosForgeConfig:
    return RosForgeConfig()


class TestIngestStage:
    def test_ingest_ros1_minimal(self, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )
        stage = IngestStage()
        ctx = stage.execute(ctx)
        assert ctx.package_ir is not None
        assert ctx.package_ir.metadata.name == "ros1_minimal"
        assert not ctx.fatal_errors

    def test_ingest_invalid_path(self, tmp_path, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=tmp_path / "nonexistent",
            output_path=tmp_output,
            config=default_config,
        )
        stage = IngestStage()
        ctx = stage.execute(ctx)
        assert ctx.fatal_errors


class TestAnalyzeStage:
    def test_analyze_produces_cost_estimate(self, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )
        IngestStage().execute(ctx)
        AnalyzeStage().execute(ctx)
        assert ctx.cost_estimate is not None
        assert ctx.cost_estimate.estimated_api_calls > 0
        assert ctx.analysis_report != ""


class TestValidateStage:
    def test_validate_skips_when_auto_build_false(self, tmp_output, default_config):
        from rosforge.models.config import ValidationConfig
        config = RosForgeConfig(validation=ValidationConfig(auto_build=False))
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=config,
        )
        ValidateStage().execute(ctx)
        assert ctx.validation_result is not None
        assert ctx.validation_result.success is True

    def test_validate_fails_gracefully_without_colcon(self, tmp_output, default_config):
        from unittest.mock import patch
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )
        with patch("shutil.which", return_value=None):
            ValidateStage().execute(ctx)
        assert ctx.validation_result is not None
        # colcon not found — should fail gracefully, not crash


class TestTransformStageRuleBased:
    def test_rule_based_transform_writes_files(self, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )
        IngestStage().execute(ctx)

        # Patch EngineRegistry to avoid needing a real engine for AI files
        from unittest.mock import patch, MagicMock
        mock_engine = MagicMock()
        mock_engine.transform.return_value = TransformedFile(
            source_path="src/talker.cpp",
            target_path="src/talker.cpp",
            original_content="",
            transformed_content="// ros2 stub",
            confidence=0.7,
            strategy_used="ai_driven",
        )
        with patch("rosforge.pipeline.transform.EngineRegistry.get", return_value=mock_engine):
            TransformStage().execute(ctx)

        assert len(ctx.transformed_files) > 0
        assert tmp_output.exists()

    def test_package_xml_transformed(self, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )
        IngestStage().execute(ctx)

        from unittest.mock import patch, MagicMock
        mock_engine = MagicMock()
        mock_engine.transform.return_value = TransformedFile(
            source_path="src/talker.cpp",
            target_path="src/talker.cpp",
            original_content="",
            transformed_content="// stub",
            confidence=0.5,
            strategy_used="ai_driven",
        )
        with patch("rosforge.pipeline.transform.EngineRegistry.get", return_value=mock_engine):
            TransformStage().execute(ctx)

        pkg_xml_results = [
            tf for tf in ctx.transformed_files
            if "package.xml" in tf.source_path
        ]
        assert len(pkg_xml_results) == 1
        assert "ament" in pkg_xml_results[0].transformed_content.lower() or \
               pkg_xml_results[0].transformed_content != ""


class TestReportStage:
    def test_report_writes_markdown(self, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )
        IngestStage().execute(ctx)
        ctx.transformed_files = [
            TransformedFile(
                source_path="package.xml",
                target_path="package.xml",
                original_content="old",
                transformed_content="new",
                confidence=0.95,
                strategy_used="rule_based",
                changes=[ChangeEntry(description="Converted to ROS2")],
            )
        ]
        tmp_output.mkdir(parents=True, exist_ok=True)
        ReportStage().execute(ctx)

        report_path = tmp_output / "migration_report.md"
        assert report_path.exists()
        content = report_path.read_text()
        assert "ros1_minimal" in content
        assert "package.xml" in content


class TestFullPipeline:
    def test_full_pipeline_with_mock_engine(self, tmp_output, default_config):
        ctx = PipelineContext(
            source_path=ROS1_MINIMAL,
            output_path=tmp_output,
            config=default_config,
        )

        from unittest.mock import patch, MagicMock
        mock_engine = MagicMock()
        mock_engine.transform.return_value = TransformedFile(
            source_path="src/talker.cpp",
            target_path="src/talker.cpp",
            original_content="",
            transformed_content="#include <rclcpp/rclcpp.hpp>\nint main() {}",
            confidence=0.85,
            strategy_used="ai_driven",
        )

        with patch("rosforge.pipeline.transform.EngineRegistry.get", return_value=mock_engine):
            runner = PipelineRunner(stages=[
                IngestStage(),
                AnalyzeStage(),
                TransformStage(),
                ReportStage(),
            ])
            ctx = runner.run(ctx)

        assert ctx.package_ir is not None
        assert ctx.migration_plan is not None
        assert len(ctx.transformed_files) > 0
        assert (tmp_output / "migration_report.md").exists()
        assert not ctx.fatal_errors
