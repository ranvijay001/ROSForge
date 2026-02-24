"""The `rosforge migrate-workspace` command."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from rosforge.cli.ui import console, print_banner, print_error, print_info, print_workspace_progress, print_workspace_summary
from rosforge.config.manager import ConfigManager
from rosforge.parsers.workspace_scanner import discover_packages, is_catkin_workspace

app = typer.Typer(help="Migrate all ROS1 packages in a catkin workspace to ROS2.")


@app.callback(invoke_without_command=True)
def migrate_workspace(
    workspace: Path = typer.Argument(..., help="Path to the catkin workspace root."),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory for migrated packages."
    ),
    engine: str = typer.Option(
        "claude", "--engine", "-e", help="AI engine to use (claude / gemini / openai)."
    ),
    mode: str = typer.Option(
        "cli", "--mode", "-m", help="Engine mode: cli or api."
    ),
    rules: Optional[Path] = typer.Option(
        None, "--rules", help="Path to a YAML file with custom transformation rules."
    ),
    max_fix_attempts: int = typer.Option(
        0, "--max-fix-attempts", help="Maximum auto-fix attempts per package (0 = disabled)."
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Auto-proceed without confirmation prompts."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output."
    ),
) -> None:
    """Migrate all ROS1 packages in a catkin workspace to ROS2."""
    print_banner()

    # ── Validate workspace path ───────────────────────────────────────────
    if not workspace.exists():
        print_error(f"Workspace path does not exist: {workspace}")
        raise typer.Exit(code=1)
    if not workspace.is_dir():
        print_error(f"Workspace path is not a directory: {workspace}")
        raise typer.Exit(code=1)
    if not is_catkin_workspace(workspace):
        print_error(
            f"{workspace} does not look like a catkin workspace. "
            "Expected a src/ directory containing at least one package.xml."
        )
        raise typer.Exit(code=1)

    # ── Discover packages ─────────────────────────────────────────────────
    package_paths = discover_packages(workspace)
    if not package_paths:
        print_error("No ROS1 packages found in the workspace src/ directory.")
        raise typer.Exit(code=1)

    print_info(f"Workspace: [bold]{workspace.resolve()}[/bold]")
    print_info(f"Packages found: [bold]{len(package_paths)}[/bold]")
    for pkg in package_paths:
        console.print(f"  [dim]•[/dim] {pkg.name}")

    # ── Determine output path ─────────────────────────────────────────────
    if output is None:
        output = workspace.parent / (workspace.resolve().name + "_ros2")
    print_info(f"Output: [bold]{output.resolve()}[/bold]")

    # ── Confirmation prompt ───────────────────────────────────────────────
    if not yes:
        import sys  # noqa: PLC0415
        if sys.stdin.isatty():
            answer = typer.prompt(
                f"Migrate {len(package_paths)} package(s)? [Y/n]", default="Y"
            )
            if answer.strip().lower() not in ("", "y", "yes"):
                print_info("Migration cancelled by user.")
                raise typer.Exit(code=0)

    # ── Load custom rules ─────────────────────────────────────────────────
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

    # ── Load config ───────────────────────────────────────────────────────
    cfg_manager = ConfigManager()
    config = cfg_manager.load()
    config = cfg_manager.set(config, "engine.name", engine)
    config = cfg_manager.set(config, "engine.mode", mode)
    if verbose:
        config = cfg_manager.set(config, "verbose", True)

    # ── Run workspace migration ───────────────────────────────────────────
    try:
        from rosforge.pipeline.workspace_runner import WorkspaceRunner  # noqa: PLC0415
    except ImportError as exc:
        print_error(f"WorkspaceRunner not available: {exc}")
        raise typer.Exit(code=1)

    runner = WorkspaceRunner(config=config, custom_rules=custom_rules)

    console.print()
    console.rule("[cyan]Starting workspace migration[/cyan]")

    # Run packages with progress display
    package_paths_resolved = [p.resolve() for p in package_paths]
    output_resolved = output.resolve()
    total = len(package_paths_resolved)
    results = []

    for idx, pkg_path in enumerate(package_paths_resolved, start=1):
        pkg_name = pkg_path.name
        print_workspace_progress(idx, total, pkg_name)
        pkg_output = output_resolved / pkg_name
        # Delegate to runner's internal method for one package at a time
        result = runner._migrate_package(pkg_name, pkg_path, pkg_output)  # noqa: SLF001
        results.append(result)
        if result.success:
            console.print(
                f"  [green]✓[/green] {pkg_name} "
                f"— {result.file_count} files, "
                f"{result.confidence_avg:.0%} avg confidence, "
                f"{result.duration_seconds:.1f}s"
            )
        else:
            console.print(f"  [red]✗[/red] {pkg_name} — {result.error_message}")

    # ── Display summary table ─────────────────────────────────────────────
    print_workspace_summary(results)

    # ── Write consolidated workspace report ───────────────────────────────
    try:
        from rosforge.pipeline.report import render_workspace_report  # noqa: PLC0415
        target_distro = config.migration.target_ros2_distro
        render_workspace_report(
            results=results,
            output_path=output_resolved,
            workspace_path=workspace.resolve(),
            target_distro=target_distro,
        )
        ws_report_path = output_resolved / "workspace_report.md"
        console.print()
        console.print(
            f"[bold green]Workspace report:[/bold green] [cyan]{ws_report_path}[/cyan]"
        )
    except Exception as exc:  # noqa: BLE001
        if verbose:
            console.print_exception()
        console.print(f"[yellow]Warning: could not write workspace report: {exc}[/yellow]")

    # ── Exit code ─────────────────────────────────────────────────────────
    failed = [r for r in results if not r.success]
    if failed:
        console.print()
        console.print(
            f"[bold red]{len(failed)} package(s) failed migration.[/bold red]"
        )
        raise typer.Exit(code=1)
