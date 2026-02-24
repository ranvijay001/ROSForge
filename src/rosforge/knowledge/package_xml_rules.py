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
    # Build tools
    "catkin": "ament_cmake",
    # Core client libraries
    "roscpp": "rclcpp",
    "rospy": "rclpy",
    # Message / interface generation
    "message_generation": "rosidl_default_generators",
    "message_runtime": "rosidl_default_runtime",
    # Actions
    "actionlib": "rclcpp_action",
    "actionlib_msgs": "action_msgs",
    # Removed packages (no direct ROS2 equivalent)
    "dynamic_reconfigure": "",
    # TF
    "tf": "tf2_ros",
    "tf2": "tf2_ros",
    "tf2_geometry_msgs": "tf2_geometry_msgs",
    "tf2_sensor_msgs": "tf2_sensor_msgs",
    "tf2_eigen": "tf2_eigen",
    # Nodelets → components
    "nodelet": "rclcpp_components",
    "nodelet_core": "rclcpp_components",
    # Plugins
    "pluginlib": "pluginlib",
    # Bag files
    "rosbag": "rosbag2_cpp",
    "rosbag_storage": "rosbag2_storage",
    # Logging / console
    "rosconsole": "rcutils",
    "rosconsole_bridge": "rcutils",
    # Index / resources
    "roslib": "ament_index_python",
    "resource_retriever": "resource_retriever",
    # Testing
    "rostest": "ament_cmake_gtest",
    "gtest": "ament_cmake_gtest",
    "gmock": "ament_cmake_gmock",
    # Math / utilities
    "angles": "angles",
    "eigen_conversions": "tf2_eigen",
    "kdl_conversions": "tf2_kdl",
    # Image / vision
    "image_transport": "image_transport",
    "cv_bridge": "cv_bridge",
    "camera_info_manager": "camera_info_manager",
    # Robot description / URDF
    "urdf": "urdf",
    "urdf_parser_plugin": "urdf",
    "robot_state_publisher": "robot_state_publisher",
    "joint_state_publisher": "joint_state_publisher",
    # Launch
    "roslaunch": "launch_ros",
    # Parameter server (removed in ROS2)
    "dynamic_reconfigure_tools": "",
    # Common message packages (unchanged names)
    "std_msgs": "std_msgs",
    "std_srvs": "std_srvs",
    "sensor_msgs": "sensor_msgs",
    "geometry_msgs": "geometry_msgs",
    "nav_msgs": "nav_msgs",
    "diagnostic_msgs": "diagnostic_msgs",
    "visualization_msgs": "visualization_msgs",
    "trajectory_msgs": "trajectory_msgs",
    "control_msgs": "control_msgs",
    "shape_msgs": "shape_msgs",
    "stereo_msgs": "stereo_msgs",
    "builtin_interfaces": "builtin_interfaces",
    "rcl_interfaces": "rcl_interfaces",
    "rosgraph_msgs": "rcl_interfaces",
    "roscpp_tutorials": "",
    "rospy_tutorials": "",
    # Diagnostics
    "diagnostic_updater": "diagnostic_updater",
    "self_test": "self_test",
    # Navigation / planning
    "costmap_2d": "nav2_costmap_2d",
    "move_base": "nav2_bringup",
    "move_base_msgs": "nav2_msgs",
    "map_server": "nav2_map_server",
    "amcl": "nav2_amcl",
    # MoveIt (name unchanged in ROS2)
    "moveit_core": "moveit_core",
    "moveit_ros_planning": "moveit_ros_planning",
    "moveit_ros_planning_interface": "moveit_ros_planning_interface",
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


# ROS1 package.xml format 1 tag → normalised DependencyType
# Format 1 uses <run_depend> (no <exec_depend>/<build_export_depend>)
_FORMAT1_TAG_MAP: dict[str, DependencyType] = {
    "build_depend": DependencyType.BUILD,
    "run_depend": DependencyType.EXEC,       # format 1 only
    "buildtool_depend": DependencyType.BUILDTOOL,
    "test_depend": DependencyType.TEST,
    "depend": DependencyType.DEPEND,
    # format 2/3 tags (kept for completeness)
    "exec_depend": DependencyType.EXEC,
    "build_export_depend": DependencyType.BUILD_EXPORT,
}


def normalize_format1_dependencies(raw_deps: list[dict[str, str]]) -> list[Dependency]:
    """Convert raw tag-name / package-name pairs from a format-1 package.xml.

    Format 1 uses ``<run_depend>`` where format 2+ uses ``<exec_depend>`` and
    ``<build_export_depend>``.  This helper normalises the old tags so the rest
    of the pipeline can treat all formats uniformly.

    Args:
        raw_deps: List of ``{"tag": "<xml-tag-name>", "name": "<pkg>"}`` dicts.

    Returns:
        List of :class:`~rosforge.models.ir.Dependency` objects.
    """
    deps: list[Dependency] = []
    for item in raw_deps:
        tag = item.get("tag", "depend")
        name = item.get("name", "")
        if not name:
            continue
        dep_type = _FORMAT1_TAG_MAP.get(tag, DependencyType.DEPEND)
        deps.append(Dependency(name=name, dep_type=dep_type))
    return deps


def transform_package_xml(
    metadata: PackageMetadata,
    dependencies: list[Dependency],
    is_metapackage: bool = False,
    group_membership: list[str] | None = None,
) -> str:
    """Generate a complete ROS2 package.xml format="3" string.

    Handles input from both format 1 and format 2/3 package.xml files.
    Format 1 ``<run_depend>`` entries are promoted to ``<exec_depend>``
    in the output.

    Args:
        metadata: Parsed package metadata from the ROS1 package.
        dependencies: All dependencies from the ROS1 package.
        is_metapackage: If True, emit ``<build_type>ament_cmake</build_type>``
            inside ``<export>`` and add ``<member_of_group>`` tags for ROS2
            metapackage convention.
        group_membership: Optional list of ROS2 group names to emit as
            ``<member_of_group>`` tags inside ``<export>``.

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

    # buildtool → ament_cmake; preserve condition attribute if present on the
    # original catkin buildtool_depend (passed through dependencies list)
    buildtool_condition: str | None = None
    for dep in dependencies:
        if dep.dep_type == DependencyType.BUILDTOOL and dep.name in ("catkin", "ament_cmake"):
            buildtool_condition = dep.condition
            break

    bt_el = ET.SubElement(root, "buildtool_depend")
    bt_el.text = "ament_cmake"
    if buildtool_condition:
        bt_el.set("condition", buildtool_condition)

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

    # Build <export> block
    export_el = ET.SubElement(root, "export")
    export_el.append(_make_element("build_type", "ament_cmake"))

    # Metapackage: add member_of_group entries
    if is_metapackage:
        export_el.append(_make_element("member_of_group", metadata.name))

    for group in (group_membership or []):
        export_el.append(_make_element("member_of_group", group))

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
