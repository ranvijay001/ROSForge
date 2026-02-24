"""Configuration model backed by TOML."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    """AI engine configuration."""

    name: str = "claude"  # claude / gemini / openai
    mode: str = "cli"  # cli / api
    timeout_seconds: int = 300
    api_key: str = ""  # only for api mode, typically from env var
    model: str = ""  # optional model override


class MigrationConfig(BaseModel):
    """Migration behavior settings."""

    target_ros2_distro: str = "humble"
    backup_original: bool = True
    init_git: bool = True
    output_dir: str = ""  # empty = auto-generate
    interactive: bool = False


class ValidationConfig(BaseModel):
    """Build validation settings."""

    auto_build: bool = True
    rosdep_install: bool = True
    max_fix_attempts: int = 0  # Phase 2: auto-fix loop


class TelemetryConfig(BaseModel):
    """Telemetry opt-in settings."""

    enabled: bool | None = None  # None = not yet asked
    local_log: bool = True


class RosForgeConfig(BaseModel):
    """Root configuration — maps to ~/.rosforge/config.toml."""

    engine: EngineConfig = Field(default_factory=EngineConfig)
    migration: MigrationConfig = Field(default_factory=MigrationConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    verbose: bool = False

    @property
    def config_dir(self) -> Path:
        return Path.home() / ".rosforge"

    @property
    def config_path(self) -> Path:
        return self.config_dir / "config.toml"

    @property
    def log_dir(self) -> Path:
        return self.config_dir / "logs"
