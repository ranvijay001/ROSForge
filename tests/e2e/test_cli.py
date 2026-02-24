"""E2E CLI tests using Typer's CliRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from rosforge.cli.app import app
from rosforge.models.result import TransformedFile

FIXTURES = Path(__file__).parent.parent / "fixtures"
ROS1_MINIMAL = FIXTURES / "ros1_minimal"

runner = CliRunner()


class TestVersionCommand:
    def test_version_exits_zero(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0

    def test_version_contains_number(self):
        result = runner.invoke(app, ["--version"])
        assert "rosforge" in result.stdout
        # Should contain a version number like "0.1.0"
        import re
        assert re.search(r"\d+\.\d+\.\d+", result.stdout)


class TestMigrateHelp:
    def test_migrate_help_exits_zero(self):
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0

    def test_migrate_help_shows_source_argument(self):
        result = runner.invoke(app, ["migrate", "--help"])
        assert "SOURCE" in result.stdout or "source" in result.stdout.lower()

    def test_migrate_help_shows_engine_option(self):
        result = runner.invoke(app, ["migrate", "--help"])
        assert "--engine" in result.stdout


class TestMigrateCommand:
    def test_migrate_missing_source_fails(self):
        result = runner.invoke(app, ["migrate", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_migrate_with_mock_engine(self, tmp_path):
        output = tmp_path / "output"

        mock_tf = TransformedFile(
            source_path="package.xml",
            target_path="package.xml",
            original_content="old",
            transformed_content="<package format=\"3\"/>",
            confidence=0.95,
            strategy_used="rule_based",
        )

        from rosforge.pipeline.runner import PipelineContext

        def fake_run(ctx):
            ctx.transformed_files = [mock_tf]
            output.mkdir(parents=True, exist_ok=True)
            (output / "migration_report.md").write_text("# Report\n")
            return ctx

        with patch("rosforge.pipeline.runner.PipelineRunner.run", side_effect=fake_run):
            with patch("rosforge.pipeline.transform.EngineRegistry.get"):
                result = runner.invoke(
                    app,
                    ["migrate", str(ROS1_MINIMAL), "--output", str(output)],
                )
        # Should exit 0 or 2 (warnings), not 1 (failure)
        assert result.exit_code in (0, 2)


class TestConfigCommand:
    def test_config_list_exits_zero(self):
        with patch("rosforge.config.manager.ConfigManager.load") as mock_load:
            from rosforge.models.config import RosForgeConfig
            mock_load.return_value = RosForgeConfig()
            result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0

    def test_config_list_shows_engine(self):
        with patch("rosforge.config.manager.ConfigManager.load") as mock_load:
            from rosforge.models.config import RosForgeConfig
            mock_load.return_value = RosForgeConfig()
            result = runner.invoke(app, ["config", "list"])
        assert "engine" in result.stdout


class TestAnalyzeCommand:
    def test_analyze_exits_zero_on_valid_package(self):
        result = runner.invoke(app, ["analyze", str(ROS1_MINIMAL)])
        assert result.exit_code == 0

    def test_analyze_json_flag(self):
        result = runner.invoke(app, ["analyze", str(ROS1_MINIMAL), "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.stdout)
        assert "package_name" in data

    def test_analyze_missing_path_fails(self):
        result = runner.invoke(app, ["analyze", "/nonexistent/path/xyz"])
        assert result.exit_code != 0

    def test_analyze_output_flag(self, tmp_path):
        report_file = tmp_path / "report.json"
        result = runner.invoke(app, ["analyze", str(ROS1_MINIMAL), "--output", str(report_file)])
        assert result.exit_code == 0
        assert report_file.exists()
        import json
        data = json.loads(report_file.read_text())
        assert "package_name" in data


class TestStatusStub:
    def test_status_not_implemented(self):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
