"""Parse CMakeLists.txt for ROS1 catkin build information."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def _extract_macro_args(text: str, macro: str) -> list[str]:
    """Extract whitespace-separated arguments from a CMake macro call.

    Handles multi-line calls by finding matching parentheses.
    """
    pattern = rf"{re.escape(macro)}\s*\("
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return []

    start = match.end()
    depth = 1
    pos = start
    while pos < len(text) and depth > 0:
        if text[pos] == "(":
            depth += 1
        elif text[pos] == ")":
            depth -= 1
        pos += 1

    inner = text[start : pos - 1]
    # Remove comments and split on whitespace
    inner = re.sub(r"#[^\n]*", "", inner)
    return [tok for tok in inner.split() if tok]


def _extract_components(args: list[str]) -> list[str]:
    """Extract values after COMPONENTS keyword."""
    try:
        idx = args.index("COMPONENTS")
        return args[idx + 1 :]
    except ValueError:
        # Some calls use REQUIRED COMPONENTS or just list after REQUIRED
        result = []
        collecting = False
        for arg in args:
            if arg in ("REQUIRED", "COMPONENTS"):
                collecting = True
                continue
            if collecting and not arg.isupper():
                result.append(arg)
            elif collecting and arg.isupper() and arg not in ("REQUIRED", "COMPONENTS"):
                break
        return result


def _extract_keyword_values(args: list[str], keyword: str) -> list[str]:
    """Extract values following a keyword until the next keyword (ALL_CAPS)."""
    try:
        idx = args.index(keyword)
    except ValueError:
        return []
    values = []
    for arg in args[idx + 1 :]:
        if arg.isupper() and len(arg) > 1:
            break
        values.append(arg)
    return values


def parse_cmake(path: Path) -> dict:
    """Parse a CMakeLists.txt file and extract catkin build information.

    Args:
        path: Path to CMakeLists.txt

    Returns:
        Dict with keys:
            project_name: str
            catkin_packages: list[str]   # from find_package COMPONENTS
            catkin_depends: list[str]    # from catkin_package CATKIN_DEPENDS
            targets: list[dict]          # executables and libraries
            install_rules: list[str]     # install() destinations
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return {
            "project_name": "",
            "catkin_packages": [],
            "catkin_depends": [],
            "targets": [],
            "install_rules": [],
        }

    # Remove line continuations for easier parsing
    text_flat = re.sub(r"\\\n", " ", text)

    # project name
    project_name = ""
    m = re.search(r"project\s*\(\s*(\S+)", text_flat, re.IGNORECASE)
    if m:
        project_name = m.group(1)

    # find_package(catkin REQUIRED COMPONENTS ...)
    catkin_packages: list[str] = []
    fp_args = _extract_macro_args(text_flat, "find_package")
    if fp_args and fp_args[0].lower() == "catkin":
        catkin_packages = _extract_components(fp_args[1:])

    # catkin_package(CATKIN_DEPENDS ...)
    catkin_depends: list[str] = []
    cp_args = _extract_macro_args(text_flat, "catkin_package")
    if cp_args:
        catkin_depends = _extract_keyword_values(cp_args, "CATKIN_DEPENDS")

    # add_executable / add_library targets
    targets: list[dict] = []
    for m in re.finditer(r"add_executable\s*\(([^)]+)\)", text_flat, re.IGNORECASE):
        parts = m.group(1).split()
        if parts:
            targets.append({"type": "executable", "name": parts[0], "sources": parts[1:]})

    for m in re.finditer(r"add_library\s*\(([^)]+)\)", text_flat, re.IGNORECASE):
        parts = m.group(1).split()
        if parts:
            # skip optional STATIC/SHARED/MODULE keyword
            name = parts[0]
            srcs = [p for p in parts[1:] if p not in ("STATIC", "SHARED", "MODULE")]
            targets.append({"type": "library", "name": name, "sources": srcs})

    # target_link_libraries — attach to existing targets
    tll_re = re.compile(r"target_link_libraries\s*\(([^)]+)\)", re.IGNORECASE)
    for m in tll_re.finditer(text_flat):
        parts = m.group(1).split()
        if not parts:
            continue
        tgt_name = parts[0]
        libs = parts[1:]
        for tgt in targets:
            if tgt["name"] == tgt_name:
                tgt.setdefault("link_libraries", []).extend(libs)

    # install rules — collect DESTINATION values
    install_rules: list[str] = []
    inst_re = re.compile(r"install\s*\(([^)]+)\)", re.IGNORECASE)
    for m in inst_re.finditer(text_flat):
        args = m.group(1).split()
        dests = _extract_keyword_values(args, "DESTINATION")
        install_rules.extend(dests)

    return {
        "project_name": project_name,
        "catkin_packages": catkin_packages,
        "catkin_depends": catkin_depends,
        "targets": targets,
        "install_rules": install_rules,
    }
