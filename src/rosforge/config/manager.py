"""ConfigManager — load, save, and mutate RosForgeConfig via TOML."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import tomli_w

from rosforge.config.defaults import DEFAULT_CONFIG
from rosforge.models.config import RosForgeConfig

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

_DEFAULT_CONFIG_PATH = Path.home() / ".rosforge" / "config.toml"


def _strip_none(data: Any) -> Any:
    """Recursively remove None values from a dict (TOML does not support null)."""
    if isinstance(data, dict):
        return {k: _strip_none(v) for k, v in data.items() if v is not None}
    return data


class ConfigManager:
    """Load, persist, and mutate ROSForge configuration."""

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self, path: Path | str | None = None) -> RosForgeConfig:
        """Load config from TOML, creating defaults if the file is missing.

        Args:
            path: Path to the TOML file. Defaults to ~/.rosforge/config.toml.

        Returns:
            Populated RosForgeConfig instance.
        """
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

        if not config_path.exists():
            config = RosForgeConfig()
            self.save(config, config_path)
            return config

        with config_path.open("rb") as fh:
            data = tomllib.load(fh)

        return RosForgeConfig.model_validate(data)

    def save(self, config: RosForgeConfig, path: Path | str | None = None) -> None:
        """Write config to a TOML file.

        Args:
            config: The configuration object to persist.
            path: Destination path. Defaults to ~/.rosforge/config.toml.
        """
        config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = _strip_none(config.model_dump())
        with config_path.open("wb") as fh:
            tomli_w.dump(data, fh)

    # ------------------------------------------------------------------
    # Dot-notation access
    # ------------------------------------------------------------------

    def get(self, config: RosForgeConfig, key: str) -> Any:
        """Retrieve a value using dot-notation.

        Args:
            config: The configuration object.
            key: Dot-separated key path, e.g. "engine.name".

        Returns:
            The value at the specified path.

        Raises:
            KeyError: If any segment of the key path does not exist.
        """
        parts = key.split(".")
        data: Any = config.model_dump()
        for part in parts:
            if not isinstance(data, dict) or part not in data:
                raise KeyError(f"Config key not found: {key!r}")
            data = data[part]
        return data

    def set(self, config: RosForgeConfig, key: str, value: Any) -> RosForgeConfig:
        """Return a new RosForgeConfig with the given dot-notation key updated.

        Args:
            config: The existing configuration object (not mutated).
            key: Dot-separated key path, e.g. "engine.timeout_seconds".
            value: New value to assign.

        Returns:
            A new RosForgeConfig instance with the updated value.

        Raises:
            KeyError: If any intermediate segment of the key path does not exist.
        """
        parts = key.split(".")
        data = config.model_dump()

        # Navigate to the parent dict and set the leaf
        node: Any = data
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"Config key not found: {key!r}")
            node = node[part]

        leaf = parts[-1]
        if not isinstance(node, dict) or leaf not in node:
            raise KeyError(f"Config key not found: {key!r}")

        node[leaf] = value
        return RosForgeConfig.model_validate(data)
