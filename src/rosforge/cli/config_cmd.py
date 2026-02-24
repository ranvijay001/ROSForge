"""config sub-command — view and mutate ROSForge configuration."""

from __future__ import annotations

import typer

from rosforge.cli.ui import console, print_error
from rosforge.config.manager import ConfigManager

app = typer.Typer(help="Manage ROSForge configuration.")
_cfg = ConfigManager()


@app.command("list")
def config_list() -> None:
    """List all current configuration values."""
    config = _cfg.load()
    import json
    data = config.model_dump()
    console.print_json(json.dumps(data, default=str))


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Dot-notation config key, e.g. engine.name"),
    value: str = typer.Argument(..., help="New value to assign."),
) -> None:
    """Set a configuration value and persist it."""
    config = _cfg.load()
    try:
        config = _cfg.set(config, key, value)
    except KeyError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1)
    _cfg.save(config)
    console.print(f"[green]Set[/green] {key} = {value!r}")
