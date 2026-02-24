"""ValidateFixLoopStage — iterative validate-then-fix loop."""

from __future__ import annotations

from rosforge.pipeline.fix import FixStage
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineStage
from rosforge.pipeline.validate import ValidateStage


class ValidateFixLoopStage(PipelineStage):
    """Stage that runs validate → fix in a loop until the build passes
    or the maximum number of fix attempts is exhausted.

    The loop runs at most ``max_attempts + 1`` validate passes:
    one initial validate and up to ``max_attempts`` fix+re-validate
    iterations.

    Args:
        max_attempts: Maximum number of fix attempts (default 3).
    """

    def __init__(self, max_attempts: int = 3) -> None:
        self._max_attempts = max_attempts

    @property
    def name(self) -> str:
        return "Validate+Fix"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        for attempt in range(self._max_attempts + 1):
            ctx = ValidateStage().execute(ctx)
            if ctx.validation_result and ctx.validation_result.success:
                break
            if attempt < self._max_attempts:
                ctx = FixStage().execute(ctx)
        return ctx
