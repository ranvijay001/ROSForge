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

    format_version = 2
    try:
        format_version = int(root.get("format", "2"))
    except (ValueError, TypeError):
        pass

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
    for tag, dep_type in _DEP_TAG_MAP.items():
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
