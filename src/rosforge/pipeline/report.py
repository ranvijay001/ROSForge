"""Report stage — generate migration_report.md in the output directory."""

from __future__ import annotations

from datetime import timezone

from rosforge.models.plan import TransformStrategy
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage

_CONFIDENCE_EMOJI = {
    "high": "green (>0.8)",
    "medium": "yellow (0.5-0.8)",
    "low": "red (<0.5)",
}


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


class ReportStage(PipelineStage):
    """Stage 5: assemble and write migration_report.md."""

    @property
    def name(self) -> str:
        return "Report"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.transformed_files and ctx.migration_plan is None:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message="No transformation data available to report.",
                    recoverable=True,
                )
            )
            return ctx

        lines: list[str] = []

        # --- Header ---
        pkg_name = ctx.package_ir.metadata.name if ctx.package_ir else "unknown"
        lines.append(f"# ROSForge Migration Report — `{pkg_name}`\n")

        if ctx.started_at:
            ts = ctx.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            lines.append(f"**Generated:** {ts}\n")

        target_distro = (
            ctx.migration_plan.target_ros2_distro if ctx.migration_plan else "humble"
        )
        lines.append(f"**Target:** ROS 2 {target_distro}\n")
        lines.append(f"**Source:** `{ctx.source_path}`\n")
        lines.append(f"**Output:** `{ctx.output_path}`\n")

        # --- Summary ---
        lines.append("\n## Summary\n")
        if ctx.migration_plan:
            lines.append(f"{ctx.migration_plan.summary}\n")
            lines.append(
                f"Overall confidence: **{_confidence_label(ctx.migration_plan.overall_confidence)}** "
                f"({ctx.migration_plan.overall_confidence:.2f})\n"
            )
            if ctx.migration_plan.warnings:
                lines.append("\n### Warnings\n")
                for w in ctx.migration_plan.warnings:
                    lines.append(f"- {w}\n")

        # --- Analysis report ---
        if ctx.analysis_report:
            lines.append("\n## Package Analysis\n")
            lines.append("```\n")
            lines.append(ctx.analysis_report)
            lines.append("```\n")

        # --- File table ---
        lines.append("\n## Transformed Files\n")
        lines.append("| File | Strategy | Confidence | Changes | Warnings |\n")
        lines.append("|------|----------|------------|---------|----------|\n")

        for tf in ctx.transformed_files:
            conf_label = _confidence_label(tf.confidence)
            change_count = len(tf.changes)
            warn_count = len(tf.warnings)
            lines.append(
                f"| `{tf.source_path}` "
                f"| {tf.strategy_used} "
                f"| {conf_label} ({tf.confidence:.2f}) "
                f"| {change_count} "
                f"| {warn_count} |\n"
            )

        # --- Detailed changes ---
        lines.append("\n## Change Details\n")
        for tf in ctx.transformed_files:
            if not tf.changes:
                continue
            lines.append(f"\n### `{tf.source_path}`\n")
            for ch in tf.changes:
                range_str = f" (lines {ch.line_range})" if ch.line_range else ""
                reason_str = f" — {ch.reason}" if ch.reason else ""
                lines.append(f"- {ch.description}{range_str}{reason_str}\n")

        # --- Warnings per file ---
        warn_files = [tf for tf in ctx.transformed_files if tf.warnings]
        if warn_files:
            lines.append("\n## File Warnings\n")
            for tf in warn_files:
                lines.append(f"\n### `{tf.source_path}`\n")
                for w in tf.warnings:
                    lines.append(f"- {w}\n")

        # --- Pipeline errors ---
        if ctx.errors:
            lines.append("\n## Pipeline Errors\n")
            for err in ctx.errors:
                recov = "recoverable" if err.recoverable else "FATAL"
                lines.append(f"- **[{err.stage_name}]** ({recov}): {err.message}\n")

        # --- Manual action items ---
        manual_actions = []
        if ctx.migration_plan:
            manual_actions = [
                a for a in ctx.migration_plan.actions
                if a.strategy == TransformStrategy.MANUAL
            ]
        low_conf_files = [tf for tf in ctx.transformed_files if tf.confidence < 0.5]

        if manual_actions or low_conf_files:
            lines.append("\n## Manual Action Required\n")
            for a in manual_actions:
                lines.append(f"- `{a.source_path}`: {a.description}\n")
            for tf in low_conf_files:
                lines.append(
                    f"- `{tf.source_path}`: low confidence ({tf.confidence:.2f}) — review carefully\n"
                )

        report_text = "".join(lines)
        ctx.migration_report = report_text

        # Write to output directory
        report_path = ctx.output_path / "migration_report.md"
        ctx.output_path.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")

        return ctx
