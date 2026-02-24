"""Rich UI components for ROSForge CLI output."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from rosforge.models.report import MigrationReport

console = Console()


def print_banner() -> None:
    """Print the ROSForge styled title banner."""
    banner = Text()
    banner.append("ROSForge", style="bold cyan")
    banner.append("  —  AI-driven ROS1 → ROS2 migration", style="dim white")
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


def print_summary(report: MigrationReport) -> None:
    """Print a Rich table summarising the migration report.

    Args:
        report: Completed MigrationReport from the pipeline.
    """
    console.print()

    # ── Top-level stats ──────────────────────────────────────────────────
    stats = Table.grid(padding=(0, 2))
    stats.add_column(style="bold")
    stats.add_column()
    stats.add_row("Package:", report.package_name or "(unknown)")
    stats.add_row("Source:", report.source_path)
    stats.add_row("Output:", report.output_path)
    stats.add_row("Target distro:", report.target_ros2_distro)
    if report.duration_seconds:
        stats.add_row("Duration:", f"{report.duration_seconds:.1f}s")
    console.print(Panel(stats, title="[bold cyan]Migration Summary[/bold cyan]", border_style="cyan"))

    # ── Counts ────────────────────────────────────────────────────────────
    counts = Table(show_header=False, box=None, padding=(0, 2))
    counts.add_column(style="bold")
    counts.add_column(justify="right")
    counts.add_row("Files processed:", str(report.total_files_processed))
    counts.add_row("Files transformed:", f"[green]{report.files_transformed}[/green]")
    counts.add_row("Files skipped:", str(report.files_skipped))
    counts.add_row("Rule-based:", str(report.rule_based_count))
    counts.add_row("AI-driven:", str(report.ai_driven_count))
    conf_pct = f"{report.overall_confidence * 100:.0f}%"
    counts.add_row("Overall confidence:", f"[yellow]{conf_pct}[/yellow]")
    console.print(counts)

    # ── File changes table ────────────────────────────────────────────────
    if report.file_changes:
        table = Table(title="File Changes", show_lines=False, border_style="dim")
        table.add_column("Source", style="dim", no_wrap=True)
        table.add_column("Target", no_wrap=True)
        table.add_column("Strategy", justify="center")
        table.add_column("Confidence", justify="right")

        for rec in report.file_changes:
            strategy_style = "green" if rec.strategy == "rule_based" else "yellow"
            conf = f"{rec.confidence * 100:.0f}%"
            table.add_row(
                rec.source_path,
                rec.target_path,
                f"[{strategy_style}]{rec.strategy}[/{strategy_style}]",
                conf,
            )
        console.print(table)

    # ── Warnings ──────────────────────────────────────────────────────────
    if report.warnings:
        console.print()
        console.print("[bold yellow]Warnings:[/bold yellow]")
        for w in report.warnings:
            console.print(f"  [yellow]•[/yellow] {w}")

    # ── Manual actions ────────────────────────────────────────────────────
    if report.manual_actions:
        console.print()
        console.print("[bold red]Manual actions required:[/bold red]")
        for action in report.manual_actions:
            console.print(f"  [red]▶[/red] {action}")


def print_error(msg: str) -> None:
    """Print a styled error message.

    Args:
        msg: Error message text.
    """
    console.print(f"[bold red]Error:[/bold red] {msg}")


def print_info(msg: str) -> None:
    """Print an informational message."""
    console.print(f"[cyan]•[/cyan] {msg}")


@contextmanager
def create_progress() -> Generator[Progress, None, None]:
    """Yield a Rich Progress context manager for pipeline stage display."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        yield progress
