"""ROS1 → ROS2 package.xml transformation rules.

Provides a static package-name mapping table and a function that generates
a complete ROS2 package.xml (format="3") string from a PackageIR.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom

from rosforge.models.ir import Dependency, DependencyType, PackageMetadata

# ROS1 package name → ROS2 package name
# Empty-string value means the package is removed in ROS2 with no equivalent.
ROS1_TO_ROS2_PACKAGES: dict[str, str] = {
    "catkin": "ament_cmake",
    "roscpp": "rclcpp",
    "rospy": "rclpy",
    "message_generation": "rosidl_default_generators",
    "message_runtime": "rosidl_default_runtime",
    "actionlib": "rclcpp_action",
    "actionlib_msgs": "action_msgs",
    "dynamic_reconfigure": "",  # removed; no direct ROS2 equivalent
    "tf": "tf2_ros",
    "tf2": "tf2_ros",
    "nodelet": "rclcpp_components",
    "pluginlib": "pluginlib",
    "rosbag": "rosbag2_cpp",
    "rosconsole": "rcutils",
    "roslib": "ament_index_python",
    "rostest": "ament_cmake_gtest",
    "gtest": "ament_cmake_gtest",
    "angles": "angles",
    # Common message packages (unchanged names)
    "std_msgs": "std_msgs",
    "sensor_msgs": "sensor_msgs",
    "geometry_msgs": "geometry_msgs",
    "nav_msgs": "nav_msgs",
    "diagnostic_msgs": "diagnostic_msgs",
    "visualization_msgs": "visualization_msgs",
    "trajectory_msgs": "trajectory_msgs",
    "control_msgs": "control_msgs",
    "shape_msgs": "shape_msgs",
    "stereo_msgs": "stereo_msgs",
}


def _map_package(name: str) -> str | None:
    """Return the ROS2 name for a ROS1 package.

    Returns ``None`` if the package is explicitly removed in ROS2.
    Returns the original name if no mapping exists (assume unchanged).
    """
    if name in ROS1_TO_ROS2_PACKAGES:
        mapped = ROS1_TO_ROS2_PACKAGES[name]
        return None if mapped == "" else mapped
    return name


def _dep_tag(dep_type: DependencyType) -> str:
    """Return the XML tag name for a dependency type."""
    mapping = {
        DependencyType.BUILD: "build_depend",
        DependencyType.BUILD_EXPORT: "build_export_depend",
        DependencyType.EXEC: "exec_depend",
        DependencyType.BUILDTOOL: "buildtool_depend",
        DependencyType.DEPEND: "depend",
        DependencyType.TEST: "test_depend",
    }
    return mapping.get(dep_type, "depend")


def transform_package_xml(
    metadata: PackageMetadata,
    dependencies: list[Dependency],
) -> str:
    """Generate a complete ROS2 package.xml format="3" string.

    Args:
        metadata: Parsed package metadata from the ROS1 package.
        dependencies: All dependencies from the ROS1 package.

    Returns:
        A pretty-printed XML string for the ROS2 package.xml.
    """
    root = ET.Element("package", attrib={"format": "3"})

    ET.SubElement(root, "name").text = metadata.name
    ET.SubElement(root, "version").text = metadata.version
    ET.SubElement(root, "description").text = metadata.description or metadata.name

    for maintainer in metadata.maintainers:
        ET.SubElement(root, "maintainer", attrib={"email": "todo@example.com"}).text = (
            maintainer
        )

    for lic in metadata.licenses:
        ET.SubElement(root, "license").text = lic

    for url in metadata.urls:
        ET.SubElement(root, "url", attrib={"type": "website"}).text = url

    # buildtool → ament_cmake
    ET.SubElement(root, "buildtool_depend").text = "ament_cmake"

    # Track already-emitted (tag, package) pairs to avoid duplicates
    seen: set[tuple[str, str]] = set()

    for dep in dependencies:
        if dep.dep_type == DependencyType.BUILDTOOL:
            # Already handled above
            continue

        ros2_name = _map_package(dep.name)
        if ros2_name is None:
            # Package removed in ROS2 — skip
            continue

        tag = _dep_tag(dep.dep_type)
        key = (tag, ros2_name)
        if key in seen:
            continue
        seen.add(key)

        el = ET.SubElement(root, tag)
        el.text = ros2_name
        if dep.version_gte:
            el.set("version_gte", dep.version_gte)
        if dep.version_lte:
            el.set("version_lte", dep.version_lte)
        if dep.condition:
            el.set("condition", dep.condition)

    ET.SubElement(root, "export").append(
        _make_element("build_type", "ament_cmake")
    )

    raw = ET.tostring(root, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    # Remove the redundant XML declaration that minidom prepends
    lines = pretty.splitlines()
    if lines and lines[0].startswith("<?xml"):
        lines = lines[1:]
    body = "\n".join(lines).strip()

    return '<?xml version="1.0"?>\n' + body + "\n"


def _make_element(tag: str, text: str) -> ET.Element:
    el = ET.Element(tag)
    el.text = text
    return el
