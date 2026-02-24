"""config sub-command — view and mutate ROSForge configuration."""

from __future__ import annotations

import json

import typer

from rosforge.cli.ui import console, print_error, print_info
from rosforge.config.manager import ConfigManager

app = typer.Typer(help="Manage ROSForge configuration.")
_cfg = ConfigManager()


@app.command("list")
def config_list() -> None:
    """List all current configuration values."""
    config = _cfg.load()
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
        raise typer.Exit(code=1) from exc
    _cfg.save(config)
    console.print(f"[green]Set[/green] {key} = {value!r}")


@app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Dot-notation config key, e.g. engine.name"),
) -> None:
    """Get a single configuration value."""
    config = _cfg.load()
    try:
        value = _cfg.get(config, key)
    except KeyError as exc:
        print_error(str(exc))
        raise typer.Exit(code=1) from exc
    console.print(f"{key} = {value!r}")


@app.command("reset")
def config_reset(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Reset configuration to defaults."""
    if not confirm:
        confirmed = typer.confirm("Reset all configuration to defaults?", default=False)
        if not confirmed:
            print_info("Reset cancelled.")
            raise typer.Exit()

    from rosforge.models.config import RosForgeConfig

    default_config = RosForgeConfig()
    _cfg.save(default_config)
    console.print("[green]Configuration reset to defaults.[/green]")


@app.command("path")
def config_path() -> None:
    """Show the path to the configuration file."""
    from rosforge.models.config import RosForgeConfig

    config_file = RosForgeConfig().config_path
    console.print(str(config_file))
