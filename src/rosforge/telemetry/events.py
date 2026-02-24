"""Telemetry event models for ROSForge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    """Base class for all telemetry events."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str


class MigrationStartEvent(TelemetryEvent):
    """Fired when a migration run begins."""

    event_type: str = "migration_start"
    engine: str
    package_file_count: int
    total_lines: int


class MigrationEndEvent(TelemetryEvent):
    """Fired when a migration run completes (success or failure)."""

    event_type: str = "migration_end"
    duration_s: float
    success: bool
    files_transformed: int
    confidence_avg: float


class BuildResultEvent(TelemetryEvent):
    """Fired after an automated build validation attempt."""

    event_type: str = "build_result"
    passed: bool
    error_count: int


class AnalyzeRunEvent(TelemetryEvent):
    """Fired after a package analysis pass."""

    event_type: str = "analyze_run"
    complexity_estimate: Optional[str] = None
    dependency_count: int
