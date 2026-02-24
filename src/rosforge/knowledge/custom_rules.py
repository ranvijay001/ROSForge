"""Custom transformation rules — load user-supplied YAML overrides.

Provides :class:`CustomRules` and :func:`load_custom_rules` for reading a
project-local YAML file that adds or overrides built-in API/package/cmake
mapping tables.

YAML schema (version 1)::

    version: 1
    api_mappings:
      cpp:
        "old::Api": "new::Api"
      python:
        "old_module.func": "new_module.func"
    package_mappings:
      old_pkg: new_pkg
    cmake_mappings:
      "find_package(old_pkg)": "find_package(new_pkg)"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CustomRules:
    """User-supplied mapping overrides loaded from a YAML file."""

    cpp_mappings: dict[str, str] = field(default_factory=dict)
    python_mappings: dict[str, str] = field(default_factory=dict)
    package_mappings: dict[str, str] = field(default_factory=dict)
    cmake_mappings: dict[str, str] = field(default_factory=dict)


def load_custom_rules(path: Path) -> CustomRules:
    """Load custom transformation rules from a YAML file.

    Args:
        path: Path to the YAML rules file.

    Returns:
        A :class:`CustomRules` instance with the parsed mappings.

    Raises:
        ImportError: If PyYAML is not installed.
        FileNotFoundError: If *path* does not exist.
        ValueError: If the YAML is invalid or the schema version is not 1.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required to load custom rules. "
            "Install it with: pip install pyyaml"
        ) from exc

    if not path.exists():
        raise FileNotFoundError(f"Custom rules file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in custom rules file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Custom rules file {path} must contain a YAML mapping at the top level."
        )

    version = data.get("version")
    if version != 1:
        raise ValueError(
            f"Unsupported custom rules version {version!r} in {path}. "
            "Only version 1 is supported."
        )

    def _extract_str_mapping(section: object, key: str) -> dict[str, str]:
        """Extract a string→string mapping from *section*, validating all values."""
        if not isinstance(section, dict):
            return {}
        raw = section.get(key)
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError(
                f"Expected a mapping for '{key}' in custom rules, got {type(raw).__name__}."
            )
        result: dict[str, str] = {}
        for k, v in raw.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError(
                    f"All keys and values in '{key}' must be strings; "
                    f"got key={k!r} ({type(k).__name__}), value={v!r} ({type(v).__name__})."
                )
            result[k] = v
        return result

    api_section = data.get("api_mappings", {})
    cpp_mappings = _extract_str_mapping(api_section, "cpp")
    python_mappings = _extract_str_mapping(api_section, "python")
    package_mappings = _extract_str_mapping(data, "package_mappings")
    cmake_mappings = _extract_str_mapping(data, "cmake_mappings")

    return CustomRules(
        cpp_mappings=cpp_mappings,
        python_mappings=python_mappings,
        package_mappings=package_mappings,
        cmake_mappings=cmake_mappings,
    )
