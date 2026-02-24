"""The `rosforge migrate` command."""

from __future__ import annotations

import sys
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
    max_fix_attempts: int = typer.Option(
        0, "--max-fix-attempts", help="Maximum number of auto-fix attempts after build failure (0 = disabled)."
    ),
    rules: Optional[Path] = typer.Option(
        None, "--rules", help="Path to a YAML file with custom transformation rules."
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Auto-proceed past cost estimate prompt."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactively review each transformed file."
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

    # ── Load custom rules (early, before pipeline construction) ───────────
    custom_rules = None
    if rules is not None:
        try:
            from rosforge.knowledge.custom_rules import load_custom_rules  # noqa: PLC0415
            custom_rules = load_custom_rules(rules)
            rule_count = (
                len(custom_rules.cpp_mappings)
                + len(custom_rules.python_mappings)
                + len(custom_rules.package_mappings)
                + len(custom_rules.cmake_mappings)
            )
            print_info(f"Custom rules loaded: [bold]{rule_count}[/bold] overrides")
        except FileNotFoundError as exc:
            print_error(str(exc))
            raise typer.Exit(code=1)
        except ValueError as exc:
            print_error(f"Invalid custom rules file: {exc}")
            raise typer.Exit(code=1)
        except ImportError as exc:
            print_error(str(exc))
            raise typer.Exit(code=1)

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
        from rosforge.pipeline.runner import PipelineContext, PipelineRunner  # noqa: PLC0415
        from rosforge.pipeline.ingest import IngestStage  # noqa: PLC0415
        from rosforge.pipeline.analyze import AnalyzeStage  # noqa: PLC0415
        from rosforge.pipeline.transform import TransformStage  # noqa: PLC0415
        from rosforge.pipeline.report import ReportStage  # noqa: PLC0415
    except ImportError as exc:
        print_error(f"Pipeline not available: {exc}")
        raise typer.Exit(code=1)

    # ── Instantiate engine for fix loop (if needed) ───────────────────────
    pipeline_engine = None
    auto_build = config.validation.auto_build
    fix_loop_enabled = auto_build or max_fix_attempts > 0

    if fix_loop_enabled:
        try:
            from rosforge.engine.base import EngineRegistry  # noqa: PLC0415
            pipeline_engine = EngineRegistry.get(engine_key, config.engine)
        except KeyError as exc:
            print_error(f"Engine not available for fix loop: {exc}")
            raise typer.Exit(code=1)

    # ── Build stage list ──────────────────────────────────────────────────
    stages = [IngestStage(), AnalyzeStage(), TransformStage()]

    if interactive:
        from rosforge.pipeline.interactive import InteractiveReviewStage  # noqa: PLC0415
        config = cfg_manager.set(config, "migration.interactive", True)
        stages.append(InteractiveReviewStage())

    if fix_loop_enabled:
        from rosforge.pipeline.validate_fix_loop import ValidateFixLoopStage  # noqa: PLC0415
        effective_max_attempts = max(max_fix_attempts, config.validation.max_fix_attempts)
        stages.append(ValidateFixLoopStage(max_attempts=effective_max_attempts))

    stages.append(ReportStage())

    # ── Build and run pipeline ────────────────────────────────────────────
    ctx = PipelineContext(
        source_path=source.resolve(),
        output_path=output.resolve(),
        config=config,
        custom_rules=custom_rules,
        engine=pipeline_engine,
        max_fix_attempts=max_fix_attempts,
    )

    # ── After-stage callback: cost estimate prompt after Analyze ─────────
    _proceed: list[bool] = [True]  # mutable flag accessible in closure

    def _after_stage(stage_name: str, pipeline_ctx: PipelineContext) -> None:
        if stage_name != "Analyze":
            return
        estimate = pipeline_ctx.cost_estimate
        if estimate is None:
            return

        # Display cost estimate
        console.print()
        console.print("[bold]Cost estimate:[/bold]")
        console.print(f"  Input tokens:  [cyan]{estimate.total_input_tokens:,}[/cyan]")
        console.print(f"  Output tokens: [cyan]{estimate.total_output_tokens:,}[/cyan]")
        console.print(f"  API calls:     [cyan]{estimate.estimated_api_calls}[/cyan]")

        # Only show dollar cost for API mode (not CLI mode)
        if mode == "api" and estimate.estimated_cost_usd > 0:
            console.print(f"  Estimated cost: [yellow]${estimate.estimated_cost_usd:.4f}[/yellow]")
        else:
            console.print("  (CLI mode — no API cost)")

        # Prompt to proceed unless --yes or non-TTY
        if yes or not sys.stdin.isatty():
            console.print("[dim]Auto-proceeding (--yes or non-interactive).[/dim]")
            return

        answer = typer.prompt("Proceed? [Y/n]", default="Y")
        if answer.strip().lower() not in ("", "y", "yes"):
            _proceed[0] = False

    runner = PipelineRunner(
        stages=stages,
        after_stage_callback=_after_stage,
    )

    try:
        ctx = runner.run(ctx)
    except Exception as exc:  # noqa: BLE001
        print_error(f"Migration failed: {exc}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)

    # ── Check if user declined after cost estimate ────────────────────────
    if not _proceed[0]:
        print_info("Migration cancelled by user.")
        raise typer.Exit(code=0)

    # ── Report outcome ────────────────────────────────────────────────────
    if ctx.fatal_errors:
        for err in ctx.fatal_errors:
            print_error(f"[{err.stage_name}] {err.message}")
        raise typer.Exit(code=1)

    # ── Interactive review summary ─────────────────────────────────────────
    if interactive:
        review_accepted = sum(
            1 for t in ctx.transformed_files if t.user_action == "accept" and t.user_reviewed
        )
        review_skipped = sum(
            1 for t in ctx.transformed_files if t.user_action == "skip" and t.user_reviewed
        )
        console.print()
        console.print(
            f"Interactive review: [green]{review_accepted} accepted[/green], "
            f"[yellow]{review_skipped} skipped[/yellow]"
        )

    # Print migration report location
    report_path = output.resolve() / "migration_report.md"
    console.print()
    console.print(
        f"[bold green]Migration complete.[/bold green] "
        f"Report: [cyan]{report_path}[/cyan]"
    )

    transformed = ctx.transformed_files
    rule_count_files = sum(1 for t in transformed if t.strategy_used == "rule_based")
    ai_count = sum(1 for t in transformed if t.strategy_used == "ai_driven")
    conf_avg = (
        sum(t.confidence for t in transformed) / len(transformed)
        if transformed else 0.0
    )

    console.print(
        f"  Files transformed: [bold]{len(transformed)}[/bold] "
        f"({rule_count_files} rule-based, {ai_count} AI-driven)"
    )
    console.print(f"  Average confidence: [yellow]{conf_avg:.0%}[/yellow]")

    # ── Confidence breakdown ──────────────────────────────────────────────
    high_conf = sum(1 for t in transformed if t.confidence > 0.8)
    medium_conf = sum(1 for t in transformed if 0.5 <= t.confidence <= 0.8)
    low_conf = sum(1 for t in transformed if t.confidence < 0.5)

    if transformed:
        console.print(
            f"  Confidence breakdown: "
            f"[green]{high_conf} HIGH[/green], "
            f"[yellow]{medium_conf} MEDIUM[/yellow], "
            f"[red]{low_conf} LOW[/red]"
        )

    if low_conf > 0:
        low_files = [t.target_path for t in transformed if t.confidence < 0.5]
        console.print()
        console.print("[bold yellow]Low-confidence files (manual review recommended):[/bold yellow]")
        for lf in low_files:
            console.print(f"  [yellow]•[/yellow] {lf}")

    # ── Fix loop summary ──────────────────────────────────────────────────
    if fix_loop_enabled and ctx.fix_attempts > 0:
        build_ok = ctx.validation_result and ctx.validation_result.success
        build_status = "[green]PASS[/green]" if build_ok else "[red]FAIL[/red]"
        console.print()
        console.print(
            f"  Fix loop: [bold]{ctx.fix_attempts}[/bold] attempt(s), "
            f"final build: {build_status}"
        )

    recoverable_warnings = [e for e in ctx.errors if e.recoverable]
    if recoverable_warnings:
        console.print()
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for w in recoverable_warnings:
            console.print(f"  [yellow]•[/yellow] [{w.stage_name}] {w.message}")
        raise typer.Exit(code=2)  # completed with warnings
