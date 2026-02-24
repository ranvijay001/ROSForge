"""Result models — outputs of Transform and Validate stages."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from rosforge.models.plan import Confidence


class ChangeEntry(BaseModel):
    """A single change made during transformation."""

    description: str
    line_range: str = ""  # e.g. "10-25"
    reason: str = ""


class TransformedFile(BaseModel):
    """Result of transforming a single source file."""

    source_path: str  # original relative path
    target_path: str  # output relative path
    original_content: str = ""
    transformed_content: str = ""
    changes: list[ChangeEntry] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_level: Confidence = Confidence.MEDIUM
    warnings: list[str] = Field(default_factory=list)
    strategy_used: str = ""  # "rule_based" or "ai_driven"

    @property
    def has_changes(self) -> bool:
        return self.original_content != self.transformed_content


class BuildError(BaseModel):
    """A structured build error from colcon."""

    file_path: str = ""
    line_number: int = 0
    message: str = ""
    severity: str = "error"  # error / warning


class ValidationResult(BaseModel):
    """Result of the Validate stage (colcon build)."""

    success: bool = False
    build_errors: list[BuildError] = Field(default_factory=list)
    warning_count: int = 0
    error_count: int = 0
    build_log: str = ""
    duration_seconds: float = 0.0


class SubprocessResult(BaseModel):
    """Defensive parsing result from CLI subprocess calls.

    Handles four states: success, timeout, error, parse_failure.
    """

    status: Literal["success", "timeout", "error", "parse_failure"]
    raw_stdout: str = ""
    raw_stderr: str = ""
    exit_code: int = -1
    parsed_json: dict | None = None
    error_message: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success" and self.parsed_json is not None
