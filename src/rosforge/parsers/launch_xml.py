"""Parse ROS1 .launch XML files."""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)


def _attribs(el) -> dict:
    """Return element attributes as a plain dict."""
    return dict(el.attrib)


def _parse_node(el) -> dict:
    return {
        "tag": "node",
        "pkg": el.get("pkg", ""),
        "type": el.get("type", ""),
        "name": el.get("name", ""),
        "ns": el.get("ns", ""),
        "args": el.get("args", ""),
        "output": el.get("output", ""),
        "respawn": el.get("respawn", "false"),
        "required": el.get("required", "false"),
        "launch_prefix": el.get("launch-prefix", ""),
        "remaps": [{"from": r.get("from", ""), "to": r.get("to", "")} for r in el.findall("remap")],
        "params": [_parse_param(p) for p in el.findall("param")],
        "rosparam": [_parse_rosparam(r) for r in el.findall("rosparam")],
    }


def _parse_param(el) -> dict:
    return {
        "tag": "param",
        "name": el.get("name", ""),
        "value": el.get("value"),
        "type": el.get("type", ""),
        "command": el.get("command"),
        "textfile": el.get("textfile"),
        "binfile": el.get("binfile"),
    }


def _parse_rosparam(el) -> dict:
    return {
        "tag": "rosparam",
        "command": el.get("command", "load"),
        "file": el.get("file"),
        "param": el.get("param"),
        "ns": el.get("ns"),
        "subst_value": el.get("subst_value", "false"),
        "content": el.text.strip() if el.text else "",
    }


def _parse_include(el) -> dict:
    return {
        "tag": "include",
        "file": el.get("file", ""),
        "ns": el.get("ns"),
        "clear_params": el.get("clear_params", "false"),
        "args": [
            {"name": a.get("name", ""), "value": a.get("value", "")} for a in el.findall("arg")
        ],
    }


def _parse_arg(el) -> dict:
    return {
        "tag": "arg",
        "name": el.get("name", ""),
        "value": el.get("value"),
        "default": el.get("default"),
        "doc": el.get("doc"),
    }


def _parse_group(el) -> dict:
    return {
        "tag": "group",
        "ns": el.get("ns"),
        "if": el.get("if"),
        "unless": el.get("unless"),
        "clear_params": el.get("clear_params", "false"),
        "children": _parse_children(el),
    }


def _parse_remap(el) -> dict:
    return {
        "tag": "remap",
        "from": el.get("from", ""),
        "to": el.get("to", ""),
    }


def _parse_children(parent) -> list[dict]:
    """Recursively parse child elements."""
    children = []
    for el in parent:
        tag = el.tag
        if tag == "node":
            children.append(_parse_node(el))
        elif tag == "param":
            children.append(_parse_param(el))
        elif tag == "rosparam":
            children.append(_parse_rosparam(el))
        elif tag == "include":
            children.append(_parse_include(el))
        elif tag == "arg":
            children.append(_parse_arg(el))
        elif tag == "group":
            children.append(_parse_group(el))
        elif tag == "remap":
            children.append(_parse_remap(el))
        else:
            children.append({"tag": tag, "attribs": _attribs(el)})
    return children


def parse_launch_xml(path: Path) -> dict:
    """Parse a ROS1 launch file.

    Args:
        path: Path to .launch file

    Returns:
        Dict with keys:
            nodes: list of node dicts
            params: list of param dicts
            rosparam: list of rosparam dicts
            includes: list of include dicts
            args: list of arg dicts
            groups: list of group dicts
            remaps: list of remap dicts
    """
    try:
        tree = etree.parse(str(path))
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", path, exc)
        return {
            "nodes": [],
            "params": [],
            "rosparam": [],
            "includes": [],
            "args": [],
            "groups": [],
            "remaps": [],
        }

    root = tree.getroot()

    result: dict = {
        "nodes": [],
        "params": [],
        "rosparam": [],
        "includes": [],
        "args": [],
        "groups": [],
        "remaps": [],
    }

    for el in root:
        tag = el.tag
        if tag == "node":
            result["nodes"].append(_parse_node(el))
        elif tag == "param":
            result["params"].append(_parse_param(el))
        elif tag == "rosparam":
            result["rosparam"].append(_parse_rosparam(el))
        elif tag == "include":
            result["includes"].append(_parse_include(el))
        elif tag == "arg":
            result["args"].append(_parse_arg(el))
        elif tag == "group":
            result["groups"].append(_parse_group(el))
        elif tag == "remap":
            result["remaps"].append(_parse_remap(el))

    return result
