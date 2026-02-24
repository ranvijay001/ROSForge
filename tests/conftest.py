"""Shared pytest fixtures for ROSForge tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.models.config import EngineConfig, RosForgeConfig, TelemetryConfig

# ── Path helpers ──────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"
ROS1_MINIMAL = FIXTURES_DIR / "ros1_minimal"
ROS1_PYTHON = FIXTURES_DIR / "ros1_python"


@pytest.fixture()
def ros1_minimal_path() -> Path:
    """Return path to the ros1_minimal C++ fixture."""
    return ROS1_MINIMAL


@pytest.fixture()
def ros1_python_path() -> Path:
    """Return path to the ros1_python fixture."""
    return ROS1_PYTHON


@pytest.fixture()
def default_config() -> RosForgeConfig:
    """Return a default RosForgeConfig suitable for testing."""
    return RosForgeConfig()


@pytest.fixture()
def engine_config() -> EngineConfig:
    """Return a minimal EngineConfig."""
    return EngineConfig(name="claude", mode="cli", timeout_seconds=30)
