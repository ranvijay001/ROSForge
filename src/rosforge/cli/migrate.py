"""The `rosforge migrate` command."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from rosforge.cli.ui import console, print_banner, print_error, print_info
from rosforge.config.manager import ConfigManager

app = typer.Typer(help="Migrate a ROS1 package to ROS2.")


@app.callback(invoke_without_command=True)
def migrate(
    source: Path = typer.Argument(..., help="Path to the ROS1 package directory."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory for the migrated package."
    ),
    engine: str = typer.Option(
        "claude", "--engine", "-e", help="AI engine to use (claude / gemini / openai)."
    ),
    mode: str = typer.Option(
        "cli", "--mode", "-m", help="Engine mode: cli or api."
    ),
    target_distro: str = typer.Option(
        "humble", "--distro", "-d", help="Target ROS2 distribution (humble / iron / jazzy)."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output."
    ),
) -> None:
    """Migrate a ROS1 package to ROS2."""
    print_banner()

    # ── Validate source ──────────────────────────────────────────────────
    if not source.exists():
        print_error(f"Source path does not exist: {source}")
        raise typer.Exit(code=1)
    if not source.is_dir():
        print_error(f"Source path is not a directory: {source}")
        raise typer.Exit(code=1)

    # ── Determine output path ─────────────────────────────────────────────
    if output is None:
        output = source.parent / (source.name + "_ros2")

    # ── Load config and apply CLI overrides ──────────────────────────────
    cfg_manager = ConfigManager()
    config = cfg_manager.load()

    config = cfg_manager.set(config, "engine.name", engine)
    config = cfg_manager.set(config, "engine.mode", mode)
    config = cfg_manager.set(config, "migration.target_ros2_distro", target_distro)
    if verbose:
        config = cfg_manager.set(config, "verbose", True)
    config = cfg_manager.set(config, "migration.output_dir", str(output))

    engine_key = f"{engine}-{mode}"
    print_info(f"Engine: [bold]{engine_key}[/bold]")
    print_info(f"Source: [bold]{source}[/bold]")
    print_info(f"Output: [bold]{output}[/bold]")
    print_info(f"Target distro: [bold]{target_distro}[/bold]")

    # ── Import pipeline components ────────────────────────────────────────
    try:
        from rosforge.pipeline.runner import PipelineContext, PipelineRunner
        from rosforge.pipeline.ingest import IngestStage
        from rosforge.pipeline.analyze import AnalyzeStage
        from rosforge.pipeline.transform import TransformStage
        from rosforge.pipeline.report import ReportStage
    except ImportError as exc:
        print_error(f"Pipeline not available: {exc}")
        raise typer.Exit(code=1)

    # ── Build and run pipeline ────────────────────────────────────────────
    ctx = PipelineContext(
        source_path=source.resolve(),
        output_path=output.resolve(),
        config=config,
    )

    runner = PipelineRunner(
        stages=[IngestStage(), AnalyzeStage(), TransformStage(), ReportStage()]
    )

    try:
        ctx = runner.run(ctx)
    except Exception as exc:  # noqa: BLE001
        print_error(f"Migration failed: {exc}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)

    # ── Report outcome ────────────────────────────────────────────────────
    if ctx.fatal_errors:
        for err in ctx.fatal_errors:
            print_error(f"[{err.stage_name}] {err.message}")
        raise typer.Exit(code=1)

    # Print migration report location
    report_path = output.resolve() / "migration_report.md"
    console.print()
    console.print(
        f"[bold green]Migration complete.[/bold green] "
        f"Report: [cyan]{report_path}[/cyan]"
    )

    transformed = ctx.transformed_files
    rule_count = sum(1 for t in transformed if t.strategy_used == "rule_based")
    ai_count = sum(1 for t in transformed if t.strategy_used == "ai_driven")
    conf_avg = (
        sum(t.confidence for t in transformed) / len(transformed)
        if transformed else 0.0
    )

    console.print(
        f"  Files transformed: [bold]{len(transformed)}[/bold] "
        f"({rule_count} rule-based, {ai_count} AI-driven)"
    )
    console.print(f"  Average confidence: [yellow]{conf_avg:.0%}[/yellow]")

    recoverable_warnings = [e for e in ctx.errors if e.recoverable]
    if recoverable_warnings:
        console.print()
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for w in recoverable_warnings:
            console.print(f"  [yellow]•[/yellow] [{w.stage_name}] {w.message}")
        raise typer.Exit(code=2)  # completed with warnings
