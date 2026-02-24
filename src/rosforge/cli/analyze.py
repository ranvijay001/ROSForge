"""analyze sub-command stub."""

from __future__ import annotations

from pathlib import Path

import typer


def analyze(
    source: Path = typer.Argument(..., help="Path to the ROS1 package directory."),
) -> None:
    """Analyse a ROS1 package and report migration complexity."""
    typer.echo("analyze: not yet implemented", err=True)
    raise typer.Exit(code=1)
