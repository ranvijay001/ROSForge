"""status sub-command — show migration status from log files."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from rosforge.cli.ui import console, print_error, print_info
from rosforge.config.manager import ConfigManager

_cfg = ConfigManager()


def status(
    output_dir: Path | None = typer.Argument(
        None,
        help="Output directory of a previous migration (defaults to most recent log).",
        exists=False,
    ),
) -> None:
    """Show the status of an in-progress or completed migration."""
    config = _cfg.load()

    # If no directory given, try the most recent log entry
    if output_dir is None:
        log_dir = config.log_dir
        if not log_dir.exists():
            print_error("No migration logs found. Run 'rosforge migrate' first.")
            raise typer.Exit(code=1)

        log_files = sorted(log_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            print_error("No migration log files found in " + str(log_dir))
            raise typer.Exit(code=1)

        log_path = log_files[0]
        _show_log_status(log_path)
        return

    # Check if it's an output directory with a migration_report.md
    output_dir = Path(output_dir)
    report_path = output_dir / "migration_report.md"
    if report_path.exists():
        _show_report_status(output_dir, report_path)
        return

    print_error(f"No migration report found in: {output_dir}")
    raise typer.Exit(code=1)


def _show_report_status(output_dir: Path, report_path: Path) -> None:
    """Display status from migration_report.md."""
    from rich.panel import Panel
    from rich.table import Table

    content = report_path.read_text(encoding="utf-8")

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Output directory:", str(output_dir))
    table.add_row("Report:", str(report_path))

    # Count files transformed (simple heuristic from report content)
    lines = content.splitlines()
    file_count = sum(1 for ln in lines if ln.startswith("| `") and "strategy" not in ln.lower())

    table.add_row("Files transformed:", str(file_count))

    if "Build Validation" in content:
        if "PASSED" in content:
            table.add_row("Build validation:", "[green]PASSED[/green]")
        elif "FAILED" in content:
            table.add_row("Build validation:", "[red]FAILED[/red]")
        else:
            table.add_row("Build validation:", "unknown")
    else:
        table.add_row("Build validation:", "[dim]not run[/dim]")

    console.print(
        Panel(table, title="[bold cyan]Migration Status[/bold cyan]", border_style="cyan")
    )
    console.print()
    print_info(f"Full report: {report_path}")


def _show_log_status(log_path: Path) -> None:
    """Display status from a JSON log file."""
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print_error(f"Failed to read log file: {exc}")
        raise typer.Exit(code=1) from exc

    from rich.panel import Panel
    from rich.table import Table

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    for key, val in data.items():
        table.add_row(f"{key}:", str(val))

    console.print(
        Panel(table, title="[bold cyan]Migration Status[/bold cyan]", border_style="cyan")
    )
