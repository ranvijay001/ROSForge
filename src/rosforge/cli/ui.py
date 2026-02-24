"""Rich UI components for ROSForge CLI output."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from rosforge.models.report import MigrationReport

if TYPE_CHECKING:
    from rosforge.models.report import AnalysisReport

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


@contextmanager
def create_pipeline_progress() -> Generator[Progress, None, None]:
    """Yield a spinner-style Rich Progress for pipeline stage names.

    Use this when individual stages don't have sub-steps — the spinner
    indicates activity without requiring a known total.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        yield progress


def print_diff(
    original: str,
    modified: str,
    filename: str = "",
    *,
    console_obj: Console | None = None,
) -> None:
    """Print a unified diff between *original* and *modified* using Rich Syntax.

    Args:
        original: Original file content.
        modified: Modified file content.
        filename: Display name for the diff header.
        console_obj: Optional Console instance (defaults to module-level console).
    """
    import difflib  # noqa: PLC0415

    _con = console_obj or console

    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            modified.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm="",
        )
    )

    if not diff_lines:
        _con.print(f"[dim]No changes in {filename}[/dim]")
        return

    diff_text = "".join(diff_lines)

    try:
        from rich.syntax import Syntax  # noqa: PLC0415

        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        _con.print(Panel(syntax, title=f"[bold cyan]Diff: {filename}[/bold cyan]", border_style="dim"))
    except Exception:  # noqa: BLE001
        _con.print(Panel(diff_text, title=f"Diff: {filename}", border_style="dim"))


def print_workspace_progress(current: int, total: int, pkg_name: str) -> None:
    """Print a one-line progress indicator for workspace migration.

    Args:
        current: 1-based index of the package currently being migrated.
        total: Total number of packages in the workspace.
        pkg_name: Name of the package being migrated.
    """
    console.print(
        f"[cyan][[/cyan]{current}/{total}[cyan]][/cyan] "
        f"Migrating [bold]{pkg_name}[/bold]..."
    )


def print_workspace_summary(results: list) -> None:  # list[PackageResult]
    """Print a Rich Table summarising per-package workspace migration results.

    Args:
        results: List of :class:`~rosforge.pipeline.workspace_runner.PackageResult`
                 instances returned by :class:`~rosforge.pipeline.workspace_runner.WorkspaceRunner`.
    """
    from rich import box  # noqa: PLC0415
    from rich.table import Table  # noqa: PLC0415

    table = Table(
        title="[bold cyan]Workspace Migration Summary[/bold cyan]",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Package", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Files", justify="right")
    table.add_column("Avg Confidence", justify="right")
    table.add_column("Notes", style="dim")

    for r in results:
        if r.success:
            status_str = "[green]SUCCESS[/green]"
            conf_str = f"[yellow]{r.confidence_avg:.0%}[/yellow]"
            notes = ""
        else:
            status_str = "[red]FAILED[/red]"
            conf_str = "—"
            notes = r.error_message[:50] if r.error_message else ""

        table.add_row(
            r.package_name,
            status_str,
            f"{r.duration_seconds:.1f}s",
            str(r.file_count),
            conf_str,
            notes,
        )

    console.print()
    console.print(table)

    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded
    total_dur = sum(r.duration_seconds for r in results)
    console.print(
        f"  [green]{succeeded} succeeded[/green], "
        f"[red]{failed} failed[/red]  "
        f"— total {total_dur:.1f}s"
    )


def print_analysis_table(report: "AnalysisReport", *, console_obj: Console | None = None) -> None:
    """Print a Rich table for an AnalysisReport.

    Args:
        report: The AnalysisReport produced by AnalyzeStage.
        console_obj: Optional Console instance.
    """
    from rich import box  # noqa: PLC0415

    _con = console_obj or console

    risk_color = (
        "green" if report.risk_score < 0.3
        else ("yellow" if report.risk_score < 0.6 else "red")
    )
    _con.print(
        Panel(
            f"[bold]{report.package_name}[/bold]\n\n"
            f"{report.summary}\n\n"
            f"Risk: [{risk_color}]{report.risk_score:.2f}[/{risk_color}]  "
            f"Confidence: [bold]{report.confidence.value}[/bold]  "
            f"Files: {report.total_files}  Lines: {report.total_lines}",
            title="[bold cyan]ROSForge Analysis[/bold cyan]",
            border_style="cyan",
        )
    )

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
        _con.print(fc_table)

    if report.warnings:
        _con.print("\n[bold yellow]Warnings:[/bold yellow]")
        for w in report.warnings:
            _con.print(f"  [yellow]•[/yellow] {w}")
