"""Unit tests for rosforge.telemetry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from rosforge.models.config import RosForgeConfig, TelemetryConfig
from rosforge.telemetry import is_enabled, prompt_opt_in
from rosforge.telemetry.collector import TelemetryCollector
from rosforge.telemetry.events import (
    AnalyzeRunEvent,
    BuildResultEvent,
    MigrationEndEvent,
    MigrationStartEvent,
    TelemetryEvent,
)


class TestIsEnabled:
    def test_enabled_when_true(self) -> None:
        config = RosForgeConfig(telemetry=TelemetryConfig(enabled=True))
        assert is_enabled(config) is True

    def test_disabled_when_false(self) -> None:
        config = RosForgeConfig(telemetry=TelemetryConfig(enabled=False))
        assert is_enabled(config) is False

    def test_disabled_when_none(self) -> None:
        config = RosForgeConfig(telemetry=TelemetryConfig(enabled=None))
        assert is_enabled(config) is False


class TestTelemetryEvents:
    def test_migration_start_event(self) -> None:
        event = MigrationStartEvent(engine="claude", package_file_count=5, total_lines=200)
        assert event.event_type == "migration_start"
        assert event.engine == "claude"
        assert event.package_file_count == 5
        assert event.timestamp is not None

    def test_migration_end_event(self) -> None:
        event = MigrationEndEvent(
            duration_s=12.5, success=True, files_transformed=3, confidence_avg=0.85
        )
        assert event.event_type == "migration_end"
        assert event.success is True

    def test_build_result_event(self) -> None:
        event = BuildResultEvent(passed=False, error_count=2)
        assert event.event_type == "build_result"
        assert event.passed is False
        assert event.error_count == 2

    def test_analyze_run_event(self) -> None:
        event = AnalyzeRunEvent(dependency_count=7, complexity_estimate="medium")
        assert event.event_type == "analyze_run"
        assert event.dependency_count == 7

    def test_event_serialization(self) -> None:
        event = MigrationStartEvent(engine="gemini", package_file_count=1, total_lines=50)
        data = event.model_dump_json()
        assert "migration_start" in data
        assert "gemini" in data


class TestTelemetryCollector:
    def test_record_does_nothing_when_local_log_false(self, tmp_path: Path) -> None:
        config = RosForgeConfig(telemetry=TelemetryConfig(enabled=True, local_log=False))
        collector = TelemetryCollector(config)
        event = BuildResultEvent(passed=True, error_count=0)

        # Should not write any file
        with patch("rosforge.telemetry.collector._TELEMETRY_PATH") as mock_path:
            collector.record(event)
            mock_path.open.assert_not_called()

    def test_record_writes_jsonl_when_local_log_true(self, tmp_path: Path) -> None:
        config = RosForgeConfig(telemetry=TelemetryConfig(enabled=True, local_log=True))
        collector = TelemetryCollector(config)
        event = BuildResultEvent(passed=True, error_count=0)

        log_path = tmp_path / "telemetry.jsonl"
        with patch("rosforge.telemetry.collector._TELEMETRY_PATH", log_path):
            collector.record(event)

        assert log_path.exists()
        lines = log_path.read_text().splitlines()
        assert len(lines) == 1
        import json
        data = json.loads(lines[0])
        assert data["event_type"] == "build_result"

    def test_record_appends_multiple_events(self, tmp_path: Path) -> None:
        config = RosForgeConfig(telemetry=TelemetryConfig(enabled=True, local_log=True))
        collector = TelemetryCollector(config)
        log_path = tmp_path / "telemetry.jsonl"

        with patch("rosforge.telemetry.collector._TELEMETRY_PATH", log_path):
            collector.record(BuildResultEvent(passed=True, error_count=0))
            collector.record(BuildResultEvent(passed=False, error_count=3))

        lines = log_path.read_text().splitlines()
        assert len(lines) == 2

    def test_flush_is_noop(self) -> None:
        config = RosForgeConfig()
        collector = TelemetryCollector(config)
        collector.flush()  # Should not raise
