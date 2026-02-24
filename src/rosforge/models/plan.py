"""Migration plan models — output of the Analyze / early Transform stage."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TransformStrategy(str, Enum):
    """How a file should be transformed."""

    RULE_BASED = "rule_based"  # deterministic, no AI needed
    AI_DRIVEN = "ai_driven"  # requires AI engine
    SKIP = "skip"  # no transformation needed
    MANUAL = "manual"  # flagged for human review


class Confidence(str, Enum):
    """Traffic-light confidence levels."""

    HIGH = "high"  # > 0.8 — likely correct
    MEDIUM = "medium"  # 0.5–0.8 — review recommended
    LOW = "low"  # < 0.5 — manual intervention likely needed


class TransformAction(BaseModel):
    """Planned action for a single file."""

    source_path: str  # relative path in original package
    target_path: str  # relative path in output package
    strategy: TransformStrategy
    description: str = ""
    estimated_complexity: int = 1  # 1-5 scale
    confidence: float = 0.0


class CostEstimate(BaseModel):
    """Token/cost estimation for AI-driven transforms."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_api_calls: int = 0
    estimated_cost_usd: float = 0.0
    engine_name: str = ""


class MigrationPlan(BaseModel):
    """Complete migration plan for a package.

    Produced during the Transform stage's planning phase.
    """

    package_name: str = ""
    target_ros2_distro: str = "humble"
    actions: list[TransformAction] = Field(default_factory=list)
    cost_estimate: CostEstimate = Field(default_factory=CostEstimate)
    overall_confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    summary: str = ""

    @property
    def ai_driven_count(self) -> int:
        return sum(1 for a in self.actions if a.strategy == TransformStrategy.AI_DRIVEN)

    @property
    def rule_based_count(self) -> int:
        return sum(1 for a in self.actions if a.strategy == TransformStrategy.RULE_BASED)
