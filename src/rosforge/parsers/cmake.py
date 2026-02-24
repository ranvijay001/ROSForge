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

    # project name — capture until whitespace or closing paren
    project_name = ""
    m = re.search(r"project\s*\(\s*([^\s)]+)", text_flat, re.IGNORECASE)
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

    # install rules — collect all DESTINATION values from all install() calls
    install_rules: list[str] = []
    # Find all install( call positions and extract args using balanced-paren helper
    for inst_match in re.finditer(r"\binstall\s*\(", text_flat, re.IGNORECASE):
        start = inst_match.end()
        depth = 1
        pos = start
        while pos < len(text_flat) and depth > 0:
            if text_flat[pos] == "(":
                depth += 1
            elif text_flat[pos] == ")":
                depth -= 1
            pos += 1
        inner = text_flat[start : pos - 1]
        inner = re.sub(r"#[^\n]*", "", inner)
        args = [tok for tok in inner.split() if tok]
        # Collect values after every DESTINATION keyword
        # A CMake keyword is all-alpha uppercase (no $, {, }, etc.)
        def _is_cmake_keyword(tok: str) -> bool:
            return bool(tok) and tok.isalpha() and tok.isupper() and len(tok) > 1

        i = 0
        while i < len(args):
            if args[i] == "DESTINATION":
                i += 1
                while i < len(args) and not (_is_cmake_keyword(args[i]) and args[i] != "DESTINATION"):
                    install_rules.append(args[i])
                    i += 1
            else:
                i += 1

    # add_message_files(FILES ...)
    msg_files: list[str] = []
    amf_args = _extract_macro_args(text_flat, "add_message_files")
    if amf_args:
        msg_files = _extract_keyword_values(amf_args, "FILES")

    # add_service_files(FILES ...)
    srv_files: list[str] = []
    asf_args = _extract_macro_args(text_flat, "add_service_files")
    if asf_args:
        srv_files = _extract_keyword_values(asf_args, "FILES")

    # add_action_files(FILES ...)
    action_files: list[str] = []
    aaf_args = _extract_macro_args(text_flat, "add_action_files")
    if aaf_args:
        action_files = _extract_keyword_values(aaf_args, "FILES")

    # generate_messages(DEPENDENCIES ...)
    msg_deps: list[str] = []
    gm_args = _extract_macro_args(text_flat, "generate_messages")
    if gm_args:
        msg_deps = _extract_keyword_values(gm_args, "DEPENDENCIES")

    return {
        "project_name": project_name,
        "catkin_packages": catkin_packages,
        "catkin_depends": catkin_depends,
        "targets": targets,
        "install_rules": install_rules,
        "msg_files": msg_files,
        "srv_files": srv_files,
        "action_files": action_files,
        "msg_deps": msg_deps,
    }
