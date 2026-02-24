"""Telemetry opt-in helpers for ROSForge."""

from __future__ import annotations

from rosforge.models.config import RosForgeConfig


def is_enabled(config: RosForgeConfig) -> bool:
    """Return True only when the user has explicitly opted in."""
    return config.telemetry.enabled is True


def prompt_opt_in() -> bool:
    """Ask the user whether to enable telemetry.

    Returns:
        True if the user opts in, False otherwise.
    """
    try:
        from rich.prompt import Confirm

        return Confirm.ask(
            "[bold]Help improve ROSForge?[/bold] "
            "Send anonymous usage data (migration stats, no code). "
            "You can change this later with [cyan]rosforge config set telemetry.enabled false[/cyan].",
            default=False,
        )
    except ImportError:
        answer = input("Help improve ROSForge? Send anonymous usage data? [y/N] ").strip().lower()
        return answer in ("y", "yes")
