"""status sub-command stub."""

from __future__ import annotations

import typer


def status() -> None:
    """Show the status of an in-progress or completed migration."""
    typer.echo("status: not yet implemented", err=True)
    raise typer.Exit(code=1)
