"""Catkin → ament_cmake CMakeLists.txt transformation rules.

Provides static mapping tables and a rule-based transformer that converts
a ROS1 catkin CMakeLists.txt into a ROS2 ament_cmake equivalent.
"""

from __future__ import annotations

import re

# Macro-level catkin → ament_cmake keyword mappings
CATKIN_TO_AMENT: dict[str, str] = {
    "catkin_package": "ament_package",
    "catkin_INCLUDE_DIRS": "ament_target_dependencies",
    "catkin_LIBRARIES": "ament_target_dependencies",
    "catkin_EXPORTED_TARGETS": "",
    "CATKIN_GLOBAL_BIN_DESTINATION": "bin",
    "CATKIN_GLOBAL_LIB_DESTINATION": "lib",
    "CATKIN_PACKAGE_BIN_DESTINATION": "lib/${PROJECT_NAME}",
    "CATKIN_PACKAGE_LIB_DESTINATION": "lib",
    "CATKIN_PACKAGE_INCLUDE_DESTINATION": "include",
    "CATKIN_PACKAGE_SHARE_DESTINATION": "share/${PROJECT_NAME}",
    "add_message_files": "rosidl_generate_interfaces",
    "add_service_files": "rosidl_generate_interfaces",
    "generate_messages": "rosidl_generate_interfaces",
}

# ROS1 package name → ROS2 package name mappings (used inside CMakeLists)
_PKG_REMAP: dict[str, str] = {
    "roscpp": "rclcpp",
    "rospy": "rclpy",
    "message_generation": "rosidl_default_generators",
    "message_runtime": "rosidl_default_runtime",
    "actionlib": "rclcpp_action",
    "actionlib_msgs": "action_msgs",
    "tf": "tf2_ros",
    "tf2": "tf2_ros",
    "dynamic_reconfigure": "",  # removed in ROS2; no direct equivalent
    "nodelet": "rclcpp_components",
    "pluginlib": "pluginlib",
    "std_msgs": "std_msgs",
    "sensor_msgs": "sensor_msgs",
    "geometry_msgs": "geometry_msgs",
    "nav_msgs": "nav_msgs",
    "diagnostic_msgs": "diagnostic_msgs",
    "visualization_msgs": "visualization_msgs",
}


def _remap_pkg(name: str) -> str:
    """Return the ROS2 name for a ROS1 package, or the original if unknown."""
    return _PKG_REMAP.get(name, name)


def transform_cmake(original: str, catkin_deps: list[str]) -> str:
    """Apply rule-based catkin → ament_cmake transformation.

    Args:
        original: Full text of the original CMakeLists.txt.
        catkin_deps: List of catkin COMPONENTS / dependencies declared in the
            original ``find_package(catkin REQUIRED COMPONENTS ...)`` call.
            These are used to emit individual ``find_package`` calls and
            ``ament_target_dependencies`` directives.

    Returns:
        Transformed CMakeLists.txt text.
    """
    lines = original.splitlines(keepends=True)
    output: list[str] = []

    # Map deps through the package remap table, drop empty (removed) packages
    ros2_deps = [_remap_pkg(d) for d in catkin_deps if _remap_pkg(d)]

    # Track whether we already emitted find_package(ament_cmake REQUIRED)
    ament_cmake_added = False
    # Track whether ament_package() is present
    ament_package_present = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # ------------------------------------------------------------------ #
        # find_package(catkin REQUIRED COMPONENTS ...) → individual find_package
        # ------------------------------------------------------------------ #
        if re.match(r"\s*find_package\s*\(\s*catkin\b", line):
            # Consume multi-line block
            block = line
            while ")" not in block and i + 1 < len(lines):
                i += 1
                block += lines[i]

            if not ament_cmake_added:
                output.append("find_package(ament_cmake REQUIRED)\n")
                ament_cmake_added = True
            for dep in ros2_deps:
                output.append(f"find_package({dep} REQUIRED)\n")
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # catkin_package(...) → ament_package()
        # ------------------------------------------------------------------ #
        if re.match(r"\s*catkin_package\s*\(", line):
            block = line
            while ")" not in block and i + 1 < len(lines):
                i += 1
                block += lines[i]
            output.append("ament_package()\n")
            ament_package_present = True
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # include_directories(${catkin_INCLUDE_DIRS} ...)
        # → ament_target_dependencies(target deps...)
        # ------------------------------------------------------------------ #
        if re.match(r"\s*include_directories\s*\(", line) and "catkin_INCLUDE_DIRS" in line:
            block = line
            while ")" not in block and i + 1 < len(lines):
                i += 1
                block += lines[i]
            if ros2_deps:
                output.append(
                    f"ament_target_dependencies(${{TARGET}} {' '.join(ros2_deps)})\n"
                )
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # target_link_libraries(target ${catkin_LIBRARIES} ...)
        # → ament_target_dependencies(target deps...)
        # ------------------------------------------------------------------ #
        if re.match(r"\s*target_link_libraries\s*\(", line) and "catkin_LIBRARIES" in line:
            block = line
            while ")" not in block and i + 1 < len(lines):
                i += 1
                block += lines[i]
            # Extract target name (first token inside parentheses)
            m = re.search(r"target_link_libraries\s*\(\s*(\S+)", block)
            target = m.group(1) if m else "${TARGET}"
            if ros2_deps:
                output.append(
                    f"ament_target_dependencies({target} {' '.join(ros2_deps)})\n"
                )
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # Inline variable / macro renames
        # ------------------------------------------------------------------ #
        line = line.replace("${catkin_INCLUDE_DIRS}", "")
        line = line.replace("${catkin_LIBRARIES}", "")
        line = line.replace("${CATKIN_DEVEL_PREFIX}", "${CMAKE_INSTALL_PREFIX}")

        # Remap package names that appear as plain tokens
        for ros1_pkg, ros2_pkg in _PKG_REMAP.items():
            if ros2_pkg:
                line = re.sub(rf"\b{re.escape(ros1_pkg)}\b", ros2_pkg, line)

        if "ament_package()" in line:
            ament_package_present = True

        output.append(line)
        i += 1

    # Ensure ament_package() appears at the end if not already present
    if not ament_package_present:
        output.append("\nament_package()\n")

    return "".join(output)
