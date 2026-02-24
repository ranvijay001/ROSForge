"""OpenAI API backend stub — Phase 1 placeholder."""

from __future__ import annotations

from rosforge.engine.base import EngineInterface
from rosforge.models.config import EngineConfig
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile


class OpenAIAPIEngine(EngineInterface):
    """OpenAI API backend (not yet implemented — Phase 1)."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config

    def analyze(self, package_ir: PackageIR) -> MigrationPlan:
        raise NotImplementedError(
            "OpenAIAPIEngine is not yet implemented. "
            "Use engine 'claude-cli' for Phase 0."
        )

    def transform(self, source_file: SourceFile, plan: MigrationPlan) -> TransformedFile:
        raise NotImplementedError(
            "OpenAIAPIEngine is not yet implemented. "
            "Use engine 'claude-cli' for Phase 0."
        )

    def estimate_cost(self, package_ir: PackageIR) -> CostEstimate:
        raise NotImplementedError(
            "OpenAIAPIEngine is not yet implemented. "
            "Use engine 'claude-cli' for Phase 0."
        )

    def health_check(self) -> bool:
        raise NotImplementedError(
            "OpenAIAPIEngine is not yet implemented. "
            "Use engine 'claude-cli' for Phase 0."
        )
