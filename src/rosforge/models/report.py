"""Report models — analysis and migration reports."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from rosforge.models.plan import Confidence


class DependencyReport(BaseModel):
    """Status of a single dependency's ROS2 availability."""

    name: str
    available_in_ros2: bool = True
    ros2_equivalent: str = ""
    notes: str = ""


class FileComplexity(BaseModel):
    """Complexity assessment for a single file."""

    relative_path: str
    file_type: str
    line_count: int = 0
    api_usage_count: int = 0
    estimated_complexity: int = 1  # 1-5
    transform_strategy: str = ""  # rule_based / ai_driven


class AnalysisReport(BaseModel):
    """Output of the Analyze stage — package assessment before migration."""

    package_name: str = ""
    total_files: int = 0
    total_lines: int = 0
    risk_score: float = 0.0  # 0.0 (trivial) – 1.0 (very complex)
    confidence: Confidence = Confidence.MEDIUM
    dependencies: list[DependencyReport] = Field(default_factory=list)
    file_complexities: list[FileComplexity] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str = ""


class FileChangeRecord(BaseModel):
    """Record of changes to a single file in the migration report."""

    source_path: str
    target_path: str
    strategy: str  # rule_based / ai_driven / skip
    confidence: float = 0.0
    confidence_level: Confidence = Confidence.MEDIUM
    changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MigrationReport(BaseModel):
    """Final report produced by the Report stage."""

    package_name: str = ""
    source_path: str = ""
    output_path: str = ""
    target_ros2_distro: str = "humble"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

    total_files_processed: int = 0
    files_transformed: int = 0
    files_skipped: int = 0
    rule_based_count: int = 0
    ai_driven_count: int = 0

    overall_confidence: float = 0.0
    overall_confidence_level: Confidence = Confidence.MEDIUM

    file_changes: list[FileChangeRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manual_actions: list[str] = Field(default_factory=list)

    engine_name: str = ""
    engine_mode: str = ""
