"""Telemetry collector — Phase 0 stub (local JSONL logging only)."""

from __future__ import annotations

import json
from pathlib import Path

from rosforge.models.config import RosForgeConfig
from rosforge.telemetry.events import TelemetryEvent

_TELEMETRY_PATH = Path.home() / ".rosforge" / "telemetry.jsonl"


class TelemetryCollector:
    """Collect and persist telemetry events locally.

    Phase 0: events are appended to ~/.rosforge/telemetry.jsonl as JSON lines.
    No data is sent over the network.
    """

    def __init__(self, config: RosForgeConfig) -> None:
        self._config = config

    def record(self, event: TelemetryEvent) -> None:
        """Append an event as a JSON line to the local telemetry log.

        Does nothing if telemetry is disabled or local_log is False.
        """
        if not self._config.telemetry.local_log:
            return

        _TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = event.model_dump_json() + "\n"
        with _TELEMETRY_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def flush(self) -> None:
        """No-op stub — reserved for Phase 1 remote upload."""
