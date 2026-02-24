"""Parse ROS1 package.xml (format 2) into PackageMetadata and Dependency lists."""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree

from rosforge.models.ir import Dependency, DependencyType, PackageMetadata

logger = logging.getLogger(__name__)

_DEP_TAG_MAP: dict[str, DependencyType] = {
    "build_depend": DependencyType.BUILD,
    "build_export_depend": DependencyType.BUILD_EXPORT,
    "exec_depend": DependencyType.EXEC,
    "buildtool_depend": DependencyType.BUILDTOOL,
    "depend": DependencyType.DEPEND,
    "test_depend": DependencyType.TEST,
}

# Format 1 only: run_depend maps to exec_depend
_FORMAT1_EXTRA_TAG_MAP: dict[str, DependencyType] = {
    "run_depend": DependencyType.EXEC,
}


def parse_package_xml(path: Path) -> tuple[PackageMetadata, list[Dependency]]:
    """Parse a package.xml file and return metadata and dependencies.

    Args:
        path: Path to package.xml

    Returns:
        Tuple of (PackageMetadata, list[Dependency])
    """
    try:
        tree = etree.parse(str(path))
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", path, exc)
        return PackageMetadata(), []

    root = tree.getroot()

    def _text(tag: str, default: str = "") -> str:
        el = root.find(tag)
        return el.text.strip() if el is not None and el.text else default

    def _text_list(tag: str) -> list[str]:
        return [el.text.strip() for el in root.findall(tag) if el.text]

    format_version = 1
    try:
        fmt_attr = root.get("format")
        if fmt_attr is not None:
            format_version = int(fmt_attr)
        else:
            # Missing format attribute defaults to format 1 per REP-0127
            format_version = 1
    except (ValueError, TypeError):
        format_version = 1

    metadata = PackageMetadata(
        name=_text("name"),
        version=_text("version", "0.0.0"),
        description=_text("description"),
        format_version=format_version,
        maintainers=_text_list("maintainer"),
        licenses=_text_list("license"),
        urls=[el.get("url", el.text or "") for el in root.findall("url") if el is not None],
        build_type=_text("export/build_type", "catkin"),
    )

    dependencies: list[Dependency] = []

    # Build combined tag map: format 1 also supports run_depend
    combined_map = dict(_DEP_TAG_MAP)
    if format_version == 1:
        combined_map.update(_FORMAT1_EXTRA_TAG_MAP)

    for tag, dep_type in combined_map.items():
        for el in root.findall(tag):
            name = el.text.strip() if el.text else ""
            if not name:
                continue
            dependencies.append(
                Dependency(
                    name=name,
                    dep_type=dep_type,
                    version_gte=el.get("version_gte"),
                    version_lte=el.get("version_lte"),
                    condition=el.get("condition"),
                )
            )

    return metadata, dependencies
