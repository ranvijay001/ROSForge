"""analyze sub-command — analyse a ROS1 package and report migration complexity."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from rosforge.models.config import RosForgeConfig
from rosforge.models.report import AnalysisReport
from rosforge.pipeline.analyze import AnalyzeStage
from rosforge.pipeline.ingest import IngestStage
from rosforge.pipeline.runner import PipelineContext, PipelineRunner


def analyze(
    source: Path = typer.Argument(..., help="Path to the ROS1 package directory."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write JSON report to this file."
    ),
    json_output: bool = typer.Option(
        False, "--json", is_flag=True, help="Print JSON report to stdout."
    ),
) -> None:
    """Analyse a ROS1 package and report migration complexity."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        _rich_available = True
    except ImportError:
        _rich_available = False

    # Validate path
    if not source.exists():
        typer.echo(f"Error: path does not exist: {source}", err=True)
        raise typer.Exit(code=1)
    if not source.is_dir():
        typer.echo(f"Error: path is not a directory: {source}", err=True)
        raise typer.Exit(code=1)

    # Build pipeline: ingest then analyze
    config = RosForgeConfig()
    ctx = PipelineContext(
        source_path=source.resolve(),
        output_path=source.resolve() / "_rosforge_out",
        config=config,
    )

    if json_output:
        # Run stages directly to avoid Rich writing to stdout
        from rosforge.pipeline.stage import PipelineError  # noqa: PLC0415
        for stage in [IngestStage(), AnalyzeStage()]:
            ctx = _run_stage_quiet(stage, ctx)
    else:
        runner = PipelineRunner([IngestStage(), AnalyzeStage()])
        ctx = runner.run(ctx)

    if ctx.fatal_errors:
        typer.echo(f"Pipeline failed: {ctx.fatal_errors[-1].message}", err=True)
        raise typer.Exit(code=1)

    # Parse the structured report from context
    try:
        report_data = json.loads(ctx.analysis_report)
        report = AnalysisReport.model_validate(report_data)
    except Exception:
        # Fallback: print raw text
        typer.echo(ctx.analysis_report)
        raise typer.Exit(code=0)

    # --json flag: dump JSON to stdout
    if json_output:
        typer.echo(report.model_dump_json(indent=2))
        if output:
            output.write_text(report.model_dump_json(indent=2))
        raise typer.Exit(code=0)

    # --output flag: write JSON to file
    if output:
        output.write_text(report.model_dump_json(indent=2))
        if not _rich_available:
            typer.echo(f"Report written to {output}")

    # Rich table output
    if _rich_available:
        console = Console()
        _print_rich_report(console, report, output)
    else:
        _print_plain_report(report, output)


def _print_rich_report(console: object, report: AnalysisReport, output: Optional[Path]) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()  # type: ignore[assignment]

    # Summary panel
    risk_color = "green" if report.risk_score < 0.3 else ("yellow" if report.risk_score < 0.6 else "red")
    console.print(
        Panel(
            f"[bold]{report.package_name}[/bold]\n\n"
            f"{report.summary}\n\n"
            f"Risk: [{risk_color}]{report.risk_score:.2f}[/{risk_color}]  "
            f"Confidence: [bold]{report.confidence.value}[/bold]  "
            f"Files: {report.total_files}  Lines: {report.total_lines}",
            title="[bold cyan]ROSForge Analysis Report[/bold cyan]",
            border_style="cyan",
        )
    )

    # Dependency table
    if report.dependencies:
        dep_table = Table(title="Dependencies", box=box.SIMPLE_HEAVY)
        dep_table.add_column("Package", style="cyan")
        dep_table.add_column("ROS2 Available", justify="center")
        dep_table.add_column("ROS2 Equivalent", style="green")
        dep_table.add_column("Notes")
        for dep in report.dependencies:
            avail = "[green]Yes[/green]" if dep.available_in_ros2 else "[red]No[/red]"
            dep_table.add_row(dep.name, avail, dep.ros2_equivalent, dep.notes)
        console.print(dep_table)

    # File complexity table
    if report.file_complexities:
        fc_table = Table(title="File Complexity", box=box.SIMPLE_HEAVY)
        fc_table.add_column("File", style="cyan")
        fc_table.add_column("Type")
        fc_table.add_column("Lines", justify="right")
        fc_table.add_column("API Usages", justify="right")
        fc_table.add_column("Complexity", justify="center")
        fc_table.add_column("Strategy")
        for fc in report.file_complexities:
            complexity_color = (
                "green" if fc.estimated_complexity <= 2
                else ("yellow" if fc.estimated_complexity == 3 else "red")
            )
            strategy_style = "yellow" if fc.transform_strategy == "ai_driven" else "green"
            fc_table.add_row(
                fc.relative_path,
                fc.file_type,
                str(fc.line_count),
                str(fc.api_usage_count),
                f"[{complexity_color}]{fc.estimated_complexity}[/{complexity_color}]",
                f"[{strategy_style}]{fc.transform_strategy}[/{strategy_style}]",
            )
        console.print(fc_table)

    # Warnings
    if report.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in report.warnings:
            console.print(f"  [yellow]•[/yellow] {w}")

    if output:
        console.print(f"\n[dim]Report written to {output}[/dim]")


def _run_stage_quiet(stage: object, ctx: object) -> object:
    """Run a single pipeline stage without any console output."""
    from rosforge.pipeline.stage import PipelineError, PipelineStage  # noqa: PLC0415
    from rosforge.pipeline.runner import PipelineContext  # noqa: PLC0415

    assert isinstance(stage, PipelineStage)
    assert isinstance(ctx, PipelineContext)
    try:
        return stage.execute(ctx)
    except Exception as exc:  # noqa: BLE001
        ctx.errors.append(
            PipelineError(stage_name=stage.name, message=str(exc), recoverable=False)
        )
        return ctx


def _print_plain_report(report: AnalysisReport, output: Optional[Path]) -> None:
    print(f"=== ROSForge Analysis: {report.package_name} ===")
    print(report.summary)
    print(f"Risk score: {report.risk_score:.2f} | Confidence: {report.confidence.value}")
    print(f"Files: {report.total_files} | Lines: {report.total_lines}")

    if report.dependencies:
        print("\nDependencies:")
        for dep in report.dependencies:
            status = "OK" if dep.available_in_ros2 else "MISSING"
            print(f"  [{status}] {dep.name} -> {dep.ros2_equivalent or '(no mapping)'}")

    if report.file_complexities:
        print("\nFile Complexity:")
        for fc in report.file_complexities:
            print(
                f"  {fc.relative_path} ({fc.file_type}) "
                f"lines={fc.line_count} complexity={fc.estimated_complexity} "
                f"strategy={fc.transform_strategy}"
            )

    if report.warnings:
        print("\nWarnings:")
        for w in report.warnings:
            print(f"  * {w}")
