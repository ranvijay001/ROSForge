"""Validate stage — Phase 0 stub: skips colcon build."""

from __future__ import annotations

from rosforge.models.result import ValidationResult
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineStage


class ValidateStage(PipelineStage):
    """Stage 4: run colcon build to validate the migration (Phase 0 stub).

    In Phase 1 this stage will call colcon build inside the output directory
    and parse compiler errors for the auto-fix loop.
    """

    @property
    def name(self) -> str:
        return "Validate"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        # Phase 0: skip actual build validation
        ctx.validation_result = ValidationResult(
            success=True,
            build_log="[Phase 0] Build validation skipped.",
        )
        return ctx
