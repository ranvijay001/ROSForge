"""ROSForge Typer application root."""

from __future__ import annotations

from typing import Optional

import typer

from rosforge import __version__

app = typer.Typer(
    name="rosforge",
    help="AI-driven ROS1 to ROS2 migration tool.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ── Sub-command: migrate ──────────────────────────────────────────────────────
from rosforge.cli.migrate import migrate as _migrate_fn  # noqa: E402

app.command("migrate", help="Migrate a ROS1 package to ROS2.")(_migrate_fn)

# ── Sub-command: config ───────────────────────────────────────────────────────
from rosforge.cli.config_cmd import app as _config_app  # noqa: E402

app.add_typer(_config_app, name="config")

# ── Sub-commands: analyze / status (stubs) ────────────────────────────────────
from rosforge.cli.analyze import analyze as _analyze_fn  # noqa: E402
from rosforge.cli.status import status as _status_fn  # noqa: E402

app.command("analyze", help="Analyse a ROS1 package (not yet implemented).")(_analyze_fn)
app.command("status", help="Show migration status (not yet implemented).")(_status_fn)


# ── Version callback ──────────────────────────────────────────────────────────

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"rosforge {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the ROSForge version and exit.",
    ),
) -> None:
    """ROSForge — AI-driven ROS1 → ROS2 migration."""
