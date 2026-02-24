"""ROS1 → ROS2 message and service definition transformation rules.

Provides ``transform_msg()``, ``transform_srv()``, and ``transform_action()``
which convert ROS1 .msg / .srv / .action files to their ROS2 equivalents.

Key transformations:
- ``Header`` → ``std_msgs/msg/Header``
- ``time`` built-in → ``builtin_interfaces/msg/Time``
- ``duration`` built-in → ``builtin_interfaces/msg/Duration``
- Package-qualified types: ``pkg/Type`` → ``pkg/msg/Type``
- Action separator (``---``) handling
"""

from __future__ import annotations

import re

# ROS1 built-in type aliases that need remapping in ROS2
_BUILTIN_TYPE_REMAP: dict[str, str] = {
    "time": "builtin_interfaces/msg/Time",
    "duration": "builtin_interfaces/msg/Duration",
    "Header": "std_msgs/msg/Header",
}

# Primitive types that are unchanged in ROS2
_PRIMITIVE_TYPES: frozenset[str] = frozenset(
    [
        "bool",
        "byte",
        "char",
        "float32",
        "float64",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "string",
        "wstring",
    ]
)

# Regex matching a field declaration line: [type][array?] field_name [= default]
_FIELD_RE = re.compile(
    r"^(\s*)"                         # leading whitespace
    r"([\w/]+)"                       # type (may include /)
    r"(\[\d*\])?"                     # optional array suffix
    r"(\s+\w+)"                       # field name
    r"(\s*(?:=.*)?)$"                 # optional default value
)

# Regex matching a constant declaration: TYPE CONST_NAME = VALUE
_CONST_RE = re.compile(
    r"^(\s*)([\w/]+)(\s+\w+\s*=\s*.+)$"
)


def _remap_type(type_str: str) -> str:
    """Return the ROS2 equivalent for a ROS1 field type.

    Rules:
    1. Primitive types and ``string`` are unchanged.
    2. ``Header`` → ``std_msgs/msg/Header``
    3. ``time`` / ``duration`` → ``builtin_interfaces/msg/Time|Duration``
    4. ``pkg/Type`` (single slash) → ``pkg/msg/Type``
    5. Types already in ``pkg/msg/Type`` form are unchanged.
    """
    # Already fully qualified ROS2 style (two slashes)
    if type_str.count("/") >= 2:
        return type_str

    # Check built-in remaps
    if type_str in _BUILTIN_TYPE_REMAP:
        return _BUILTIN_TYPE_REMAP[type_str]

    # Primitive types unchanged
    if type_str in _PRIMITIVE_TYPES:
        return type_str

    # Package-qualified: pkg/Type → pkg/msg/Type
    if "/" in type_str:
        parts = type_str.split("/", 1)
        pkg, msg_type = parts[0], parts[1]
        # If msg_type itself looks like it already has a sub-namespace skip
        if "/" not in msg_type:
            return f"{pkg}/msg/{msg_type}"
        return type_str

    # Bare type (no package prefix) — leave unchanged, may be in same package
    return type_str


def _transform_field_line(line: str) -> str:
    """Transform a single field declaration line."""
    stripped = line.rstrip()
    if not stripped or stripped.lstrip().startswith("#"):
        return line

    # Check for separator line
    if stripped.strip() == "---":
        return line

    m = _FIELD_RE.match(stripped)
    if m:
        leading, type_str, array_suffix, field_name, default = m.groups()
        new_type = _remap_type(type_str)
        arr = array_suffix or ""
        # Reconstruct line preserving trailing newline
        suffix = "\n" if line.endswith("\n") else ""
        return f"{leading}{new_type}{arr}{field_name}{default or ''}{suffix}"

    return line


def _transform_section(section: str) -> str:
    """Transform a single section (between --- separators)."""
    result_lines = []
    for line in section.splitlines(keepends=True):
        result_lines.append(_transform_field_line(line))
    return "".join(result_lines)


def transform_msg(original: str) -> str:
    """Transform a ROS1 .msg file to ROS2 format.

    Args:
        original: Full text of the ROS1 .msg file.

    Returns:
        Transformed .msg file text with ROS2-compatible type references.
    """
    return _transform_section(original)


def transform_srv(original: str) -> str:
    """Transform a ROS1 .srv file to ROS2 format.

    Args:
        original: Full text of the ROS1 .srv file (request ``---`` response).

    Returns:
        Transformed .srv file text with ROS2-compatible type references.
    """
    # Split on separator, transform each section independently
    if "---" in original:
        parts = original.split("---", 1)
        request = _transform_section(parts[0])
        response = _transform_section(parts[1])
        return f"{request}---{response}"
    return _transform_section(original)


def transform_action(original: str) -> str:
    """Transform a ROS1 .action file to ROS2 format.

    Args:
        original: Full text of the ROS1 .action file
                  (goal ``---`` result ``---`` feedback).

    Returns:
        Transformed .action file text with ROS2-compatible type references.
    """
    parts = original.split("---")
    transformed = [_transform_section(p) for p in parts]
    return "---".join(transformed)
