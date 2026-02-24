"""Parse ROS1 .msg, .srv, and .action definition files."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Built-in ROS1 field types
_BUILTIN_TYPES = frozenset(
    {
        "bool",
        "int8",
        "uint8",
        "int16",
        "uint16",
        "int32",
        "uint32",
        "int64",
        "uint64",
        "float32",
        "float64",
        "string",
        "time",
        "duration",
        "byte",
        "char",
        # Header is technically a message but treated as builtin
        "Header",
    }
)

_COMMENT_RE = re.compile(r"#.*$")
_CONSTANT_RE = re.compile(r"^(\w+)\s+(\w+)\s*=\s*(.+)$")
_FIELD_RE = re.compile(r"^(\w+(?:/\w+)?(?:\[\d*\])?)\s+(\w+)$")
_SEPARATOR = "---"


def _strip_comment(line: str) -> str:
    return _COMMENT_RE.sub("", line).strip()


def _parse_fields(lines: list[str]) -> tuple[list[dict], list[dict]]:
    """Parse a block of lines into fields and constants.

    Returns:
        (fields, constants) where each item is a dict.
    """
    fields: list[dict] = []
    constants: list[dict] = []

    for raw in lines:
        line = _strip_comment(raw)
        if not line:
            continue

        # Try constant first: TYPE NAME = VALUE
        m = _CONSTANT_RE.match(line)
        if m:
            constants.append(
                {
                    "type": m.group(1),
                    "name": m.group(2),
                    "value": m.group(3).strip(),
                }
            )
            continue

        # Try field: TYPE NAME  (with optional array suffix on type)
        m = _FIELD_RE.match(line)
        if m:
            raw_type = m.group(1)
            name = m.group(2)
            # Determine if array
            array = False
            array_size = None
            if "[" in raw_type:
                base_type = raw_type[: raw_type.index("[")]
                bracket = raw_type[raw_type.index("[") + 1 : raw_type.index("]")]
                array = True
                array_size = int(bracket) if bracket.isdigit() else None
            else:
                base_type = raw_type

            is_builtin = base_type in _BUILTIN_TYPES or (
                "/" not in base_type and base_type[0].islower()
            )
            fields.append(
                {
                    "type": base_type,
                    "name": name,
                    "array": array,
                    "array_size": array_size,
                    "builtin": is_builtin,
                }
            )

    return fields, constants


def parse_msg_srv(path: Path) -> dict:
    """Parse a ROS1 .msg, .srv, or .action definition file.

    Args:
        path: Path to .msg, .srv, or .action file

    Returns:
        For .msg:
            {"kind": "msg", "fields": [...], "constants": [...]}
        For .srv:
            {"kind": "srv",
             "request": {"fields": [...], "constants": [...]},
             "response": {"fields": [...], "constants": [...]}}
        For .action:
            {"kind": "action",
             "goal": {"fields": [...], "constants": [...]},
             "result": {"fields": [...], "constants": [...]},
             "feedback": {"fields": [...], "constants": [...]}}
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return {}

    lines = text.splitlines()
    suffix = path.suffix.lower()

    if suffix == ".msg":
        fields, constants = _parse_fields(lines)
        return {"kind": "msg", "fields": fields, "constants": constants}

    elif suffix == ".srv":
        # Split on first '---'
        try:
            sep_idx = lines.index(_SEPARATOR)
        except ValueError:
            # No separator — treat all as request
            sep_idx = len(lines)

        req_lines = lines[:sep_idx]
        res_lines = lines[sep_idx + 1 :] if sep_idx < len(lines) else []

        req_fields, req_consts = _parse_fields(req_lines)
        res_fields, res_consts = _parse_fields(res_lines)

        return {
            "kind": "srv",
            "request": {"fields": req_fields, "constants": req_consts},
            "response": {"fields": res_fields, "constants": res_consts},
        }

    elif suffix == ".action":
        # Split on up to 3 '---' separators (goal / result / feedback)
        sections: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if line.strip() == _SEPARATOR:
                sections.append(current)
                current = []
            else:
                current.append(line)
        sections.append(current)

        # Pad to 3 sections if missing
        while len(sections) < 3:
            sections.append([])

        goal_fields, goal_consts = _parse_fields(sections[0])
        result_fields, result_consts = _parse_fields(sections[1])
        fb_fields, fb_consts = _parse_fields(sections[2])

        return {
            "kind": "action",
            "goal": {"fields": goal_fields, "constants": goal_consts},
            "result": {"fields": result_fields, "constants": result_consts},
            "feedback": {"fields": fb_fields, "constants": fb_consts},
        }

    else:
        # Unknown extension — try to parse as message
        logger.warning("Unknown extension %s for %s, parsing as .msg", suffix, path)
        fields, constants = _parse_fields(lines)
        return {"kind": "msg", "fields": fields, "constants": constants}
