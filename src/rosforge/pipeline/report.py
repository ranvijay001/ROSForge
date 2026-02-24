"""Report stage — generate migration_report.md in the output directory."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from rosforge.models.plan import TransformStrategy
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage

if TYPE_CHECKING:
    from rosforge.pipeline.workspace_runner import PackageResult


def _confidence_label(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    if score >= 0.5:
        return "MEDIUM"
    return "LOW"


def _render_jinja2(ctx: PipelineContext) -> str | None:
    """Render the migration report using the Jinja2 template.

    Returns the rendered string, or None if jinja2 is unavailable.
    """
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        return None

    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        keep_trailing_newline=True,
    )

    # Register helper as a global callable inside templates
    env.globals["confidence_label_for"] = _confidence_label

    template = env.get_template("migration_report.md.j2")

    pkg_name = ctx.package_ir.metadata.name if ctx.package_ir else "unknown"
    generated_at = ""
    if ctx.started_at:
        generated_at = ctx.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    duration_seconds: float | None = None
    if ctx.started_at and ctx.completed_at:
        duration_seconds = (ctx.completed_at - ctx.started_at).total_seconds()

    target_distro = ctx.migration_plan.target_ros2_distro if ctx.migration_plan else "humble"

    manual_actions = []
    if ctx.migration_plan:
        manual_actions = [
            a for a in ctx.migration_plan.actions if a.strategy == TransformStrategy.MANUAL
        ]

    low_conf_files = [tf for tf in ctx.transformed_files if tf.confidence < 0.5]
    warn_files = [tf for tf in ctx.transformed_files if tf.warnings]

    high_conf_count = sum(1 for tf in ctx.transformed_files if tf.confidence >= 0.8)
    medium_conf_count = sum(1 for tf in ctx.transformed_files if 0.5 <= tf.confidence < 0.8)
    low_conf_count = len(low_conf_files)

    confidence_label = (
        _confidence_label(ctx.migration_plan.overall_confidence)
        if ctx.migration_plan
        else "UNKNOWN"
    )

    # Try to get a git diff stat from the output directory
    git_diff_stat = _get_git_diff_stat(ctx.output_path)

    rendered = template.render(
        pkg_name=pkg_name,
        generated_at=generated_at,
        target_distro=target_distro,
        source_path=str(ctx.source_path),
        output_path=str(ctx.output_path),
        duration_seconds=duration_seconds,
        migration_plan=ctx.migration_plan,
        confidence_label=confidence_label,
        high_conf_count=high_conf_count,
        medium_conf_count=medium_conf_count,
        low_conf_count=low_conf_count,
        cost_estimate=ctx.cost_estimate,
        transformed_files=ctx.transformed_files,
        warn_files=warn_files,
        manual_actions=manual_actions,
        low_conf_files=low_conf_files,
        errors=ctx.errors,
        validation_result=ctx.validation_result,
        git_diff_stat=git_diff_stat,
    )
    return rendered


def _get_git_diff_stat(output_path: Path) -> str:
    """Return git diff --stat output for the output directory, or empty string."""
    try:
        from rosforge.utils.git import get_diff_stat, is_git_repo

        if is_git_repo(output_path):
            return get_diff_stat(output_path)
    except Exception:
        pass
    return ""


def _render_fallback(ctx: PipelineContext) -> str:
    """Render using plain string building (no Jinja2 dependency)."""
    lines: list[str] = []

    pkg_name = ctx.package_ir.metadata.name if ctx.package_ir else "unknown"
    lines.append(f"# ROSForge Migration Report — `{pkg_name}`\n")

    if ctx.started_at:
        ts = ctx.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"**Generated:** {ts}\n")

    target_distro = ctx.migration_plan.target_ros2_distro if ctx.migration_plan else "humble"
    lines.append(f"**Target:** ROS 2 {target_distro}\n")
    lines.append(f"**Source:** `{ctx.source_path}`\n")
    lines.append(f"**Output:** `{ctx.output_path}`\n")

    if ctx.started_at and ctx.completed_at:
        dur = (ctx.completed_at - ctx.started_at).total_seconds()
        lines.append(f"**Duration:** {dur:.1f}s\n")

    lines.append("\n## Summary\n")
    if ctx.migration_plan:
        lines.append(f"{ctx.migration_plan.summary}\n")
        conf_label = _confidence_label(ctx.migration_plan.overall_confidence)
        lines.append(
            f"Overall confidence: **{conf_label}** ({ctx.migration_plan.overall_confidence:.2f})\n"
        )
        if ctx.migration_plan.warnings:
            lines.append("\n### Warnings\n")
            for w in ctx.migration_plan.warnings:
                lines.append(f"- {w}\n")

    # Confidence table
    high_count = sum(1 for tf in ctx.transformed_files if tf.confidence >= 0.8)
    med_count = sum(1 for tf in ctx.transformed_files if 0.5 <= tf.confidence < 0.8)
    low_count = sum(1 for tf in ctx.transformed_files if tf.confidence < 0.5)
    lines.append("\n## Confidence Table\n")
    lines.append("| Level | Files |\n")
    lines.append("|-------|-------|\n")
    lines.append(f"| HIGH (>=0.8) | {high_count} |\n")
    lines.append(f"| MEDIUM (0.5-0.8) | {med_count} |\n")
    lines.append(f"| LOW (<0.5) | {low_count} |\n")

    # Cost estimate
    if ctx.cost_estimate:
        ce = ctx.cost_estimate
        lines.append("\n## Cost Estimate\n")
        lines.append(f"- Input tokens: {ce.total_input_tokens}\n")
        lines.append(f"- Output tokens: {ce.total_output_tokens}\n")
        lines.append(f"- Estimated cost: ${ce.estimated_cost_usd:.4f}\n")
        lines.append(f"- Engine: {ce.engine_name}\n")

    # Analysis
    if ctx.analysis_report:
        lines.append("\n## Package Analysis\n")
        lines.append("```\n")
        lines.append(ctx.analysis_report)
        lines.append("```\n")

    # File table
    lines.append("\n## Transformed Files\n")
    lines.append("| File | Strategy | Confidence | Changes | Warnings |\n")
    lines.append("|------|----------|------------|---------|----------|\n")
    for tf in ctx.transformed_files:
        conf_label = _confidence_label(tf.confidence)
        lines.append(
            f"| `{tf.source_path}` "
            f"| {tf.strategy_used} "
            f"| {conf_label} ({tf.confidence:.2f}) "
            f"| {len(tf.changes)} "
            f"| {len(tf.warnings)} |\n"
        )

    # Detailed changes
    lines.append("\n## Change Details\n")
    for tf in ctx.transformed_files:
        if not tf.changes:
            continue
        lines.append(f"\n### `{tf.source_path}`\n")
        for ch in tf.changes:
            range_str = f" (lines {ch.line_range})" if ch.line_range else ""
            reason_str = f" — {ch.reason}" if ch.reason else ""
            lines.append(f"- {ch.description}{range_str}{reason_str}\n")

    # Git diff stat
    git_diff_stat = _get_git_diff_stat(ctx.output_path)
    if git_diff_stat:
        lines.append("\n## Git Diff Summary\n")
        lines.append("```\n")
        lines.append(git_diff_stat)
        lines.append("```\n")

    # Warnings per file
    warn_files = [tf for tf in ctx.transformed_files if tf.warnings]
    if warn_files:
        lines.append("\n## File Warnings\n")
        for tf in warn_files:
            lines.append(f"\n### `{tf.source_path}`\n")
            for w in tf.warnings:
                lines.append(f"- {w}\n")

    # Pipeline errors
    if ctx.errors:
        lines.append("\n## Pipeline Errors\n")
        for err in ctx.errors:
            recov = "recoverable" if err.recoverable else "FATAL"
            lines.append(f"- **[{err.stage_name}]** ({recov}): {err.message}\n")

    # Manual actions
    manual_actions = []
    if ctx.migration_plan:
        manual_actions = [
            a for a in ctx.migration_plan.actions if a.strategy == TransformStrategy.MANUAL
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

    return "".join(lines)


class ReportStage(PipelineStage):
    """Stage 5: assemble and write migration_report.md.

    Uses the Jinja2 template at ``src/rosforge/templates/migration_report.md.j2``
    when jinja2 is available, falling back to inline string building otherwise.
    """

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

        # Attempt Jinja2 render, fall back to plain renderer
        report_text = _render_jinja2(ctx)
        if report_text is None:
            report_text = _render_fallback(ctx)

        ctx.migration_report = report_text

        report_path = ctx.output_path / "migration_report.md"
        ctx.output_path.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8")

        return ctx


def render_workspace_report(
    results: list[PackageResult],
    output_path: Path,
    workspace_path: Path,
    target_distro: str = "humble",
) -> str:
    """Render and write a workspace-level ``workspace_report.md``.

    Tries the Jinja2 template first, falls back to a plain Markdown string.

    Args:
        results: Ordered list of per-package migration results.
        output_path: Directory where ``workspace_report.md`` is written.
        workspace_path: Original catkin workspace root (for display).
        target_distro: Target ROS 2 distribution name.

    Returns:
        Rendered report text.
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_duration = sum(r.duration_seconds for r in results)
    total_files = sum(r.file_count for r in results)
    failed_packages = [r for r in results if not r.success]

    report_text = _render_workspace_jinja2(
        results=results,
        workspace_path=workspace_path,
        output_path=output_path,
        generated_at=generated_at,
        target_distro=target_distro,
        total_duration=total_duration,
        total_files=total_files,
        failed_packages=failed_packages,
    )
    if report_text is None:
        report_text = _render_workspace_fallback(
            results=results,
            workspace_path=workspace_path,
            output_path=output_path,
            generated_at=generated_at,
            target_distro=target_distro,
            total_duration=total_duration,
            total_files=total_files,
            failed_packages=failed_packages,
        )

    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "workspace_report.md").write_text(report_text, encoding="utf-8")
    return report_text


def _render_workspace_jinja2(
    results: list[PackageResult],
    workspace_path: Path,
    output_path: Path,
    generated_at: str,
    target_distro: str,
    total_duration: float,
    total_files: int,
    failed_packages: list[PackageResult],
) -> str | None:
    """Render workspace report via Jinja2 template. Returns None if unavailable."""
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        return None

    template_dir = Path(__file__).parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("workspace_report.md.j2")
    return template.render(
        results=results,
        workspace_path=str(workspace_path),
        output_path=str(output_path),
        generated_at=generated_at,
        target_distro=target_distro,
        total_duration=total_duration,
        total_files=total_files,
        failed_packages=failed_packages,
    )


def _render_workspace_fallback(
    results: list[PackageResult],
    workspace_path: Path,
    output_path: Path,
    generated_at: str,
    target_distro: str,
    total_duration: float,
    total_files: int,
    failed_packages: list[PackageResult],
) -> str:
    """Plain Markdown workspace report (no Jinja2 dependency)."""
    succeeded = [r for r in results if r.success]
    lines: list[str] = [
        "# ROSForge Workspace Migration Report\n\n",
        f"**Workspace:** `{workspace_path}`\n",
        f"**Output:** `{output_path}`\n",
        f"**Generated:** {generated_at}\n",
        f"**Target:** ROS 2 {target_distro}\n\n",
        "---\n\n## Summary\n\n",
        f"- Total packages: {len(results)}\n",
        f"- Succeeded: {len(succeeded)}\n",
        f"- Failed: {len(failed_packages)}\n",
        f"- Total duration: {total_duration:.1f}s\n",
        f"- Files transformed: {total_files}\n\n",
        "---\n\n## Per-Package Results\n\n",
        "| Package | Status | Duration | Files | Avg Confidence |\n",
        "|---------|--------|----------|-------|----------------|\n",
    ]
    for r in results:
        status = "SUCCESS" if r.success else "FAILED"
        conf = f"{r.confidence_avg:.0%}" if r.success else "—"
        lines.append(
            f"| `{r.package_name}` | {status} | {r.duration_seconds:.1f}s"
            f" | {r.file_count} | {conf} |\n"
        )

    if failed_packages:
        lines.append("\n---\n\n## Failed Packages\n\n")
        for r in failed_packages:
            lines.append(f"### `{r.package_name}`\n\n")
            lines.append(f"**Error:** {r.error_message}\n\n")

    return "".join(lines)
