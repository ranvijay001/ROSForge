"""Unit tests for ReportStage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.models.result import ChangeEntry, TransformedFile
from rosforge.pipeline.report import ReportStage, _confidence_label
from rosforge.pipeline.runner import PipelineContext


class TestConfidenceLabel:
    def test_high(self) -> None:
        assert _confidence_label(0.9) == "HIGH"
        assert _confidence_label(0.8) == "HIGH"

    def test_medium(self) -> None:
        assert _confidence_label(0.7) == "MEDIUM"
        assert _confidence_label(0.5) == "MEDIUM"

    def test_low(self) -> None:
        assert _confidence_label(0.4) == "LOW"
        assert _confidence_label(0.0) == "LOW"


class TestReportStage:
    def _make_ctx(self, tmp_path: Path) -> PipelineContext:
        config = RosForgeConfig()
        ctx = PipelineContext(
            source_path=tmp_path / "src",
            output_path=tmp_path / "out",
            config=config,
        )
        ctx.transformed_files = [
            TransformedFile(
                source_path="src/node.cpp",
                target_path="src/node.cpp",
                confidence=0.9,
                strategy_used="rule_based",
                changes=[ChangeEntry(description="Replaced ros::init", line_range="5-5")],
            ),
            TransformedFile(
                source_path="scripts/monitor.py",
                target_path="scripts/monitor.py",
                confidence=0.4,
                strategy_used="ai_driven",
                warnings=["Manual review needed"],
            ),
        ]
        return ctx

    def test_writes_report_file(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path)
        (tmp_path / "out").mkdir(parents=True)
        stage = ReportStage()
        stage.execute(ctx)
        report_path = tmp_path / "out" / "migration_report.md"
        assert report_path.exists()

    def test_report_contains_pkg_info(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path)
        (tmp_path / "out").mkdir(parents=True)
        stage = ReportStage()
        result_ctx = stage.execute(ctx)
        assert result_ctx.migration_report != ""
        # Should contain some key sections
        report = result_ctx.migration_report
        assert "node.cpp" in report or "monitor.py" in report

    def test_no_data_adds_error(self, tmp_path: Path) -> None:
        config = RosForgeConfig()
        ctx = PipelineContext(
            source_path=tmp_path / "src",
            output_path=tmp_path / "out",
            config=config,
        )
        stage = ReportStage()
        result_ctx = stage.execute(ctx)
        assert len(result_ctx.errors) > 0
        assert any("No transformation data" in e.message for e in result_ctx.errors)

    def test_fallback_render_used_when_jinja2_unavailable(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path)
        (tmp_path / "out").mkdir(parents=True)
        stage = ReportStage()

        # Mock jinja2 as unavailable
        with patch("rosforge.pipeline.report._render_jinja2", return_value=None):
            result_ctx = stage.execute(ctx)

        assert result_ctx.migration_report != ""
        assert "Transformed Files" in result_ctx.migration_report

    def test_stage_name(self) -> None:
        assert ReportStage().name == "Report"

    def test_confidence_table_in_fallback(self, tmp_path: Path) -> None:
        ctx = self._make_ctx(tmp_path)
        (tmp_path / "out").mkdir(parents=True)
        stage = ReportStage()

        with patch("rosforge.pipeline.report._render_jinja2", return_value=None):
            result_ctx = stage.execute(ctx)

        assert "Confidence Table" in result_ctx.migration_report
