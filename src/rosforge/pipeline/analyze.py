"""Analyze stage — Phase 0 stub: basic complexity estimate only."""

from __future__ import annotations

from rosforge.models.plan import CostEstimate
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage


class AnalyzeStage(PipelineStage):
    """Stage 2: estimate migration complexity (Phase 0 — rule-based only).

    In Phase 1 this stage will call engine.analyze() for a full AI-driven plan.
    For Phase 0 it produces a lightweight cost estimate from IR statistics.
    """

    @property
    def name(self) -> str:
        return "Analyze"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.package_ir is None:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message="PackageIR is not available — Ingest stage must run first.",
                    recoverable=False,
                )
            )
            return ctx

        ir = ctx.package_ir
        # Rough token estimate: ~500 tokens per file for system prompt + content
        input_tokens = ir.total_lines * 2 + ir.total_files * 500
        output_tokens = int(input_tokens * 0.20)

        ctx.cost_estimate = CostEstimate(
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            estimated_api_calls=max(1, ir.total_files),
            estimated_cost_usd=0.0,
            engine_name=ctx.config.engine.name + "-" + ctx.config.engine.mode,
        )

        ctx.analysis_report = (
            f"Package: {ir.metadata.name} v{ir.metadata.version}\n"
            f"Files: {ir.total_files} ({ir.cpp_files} C++, "
            f"{ir.python_files} Python, {ir.launch_files} launch, "
            f"{ir.msg_srv_files} msg/srv)\n"
            f"Lines: {ir.total_lines}\n"
            f"Dependencies: {len(ir.dependencies)}\n"
            f"API usages detected: {len(ir.api_usages)}\n"
        )

        return ctx
