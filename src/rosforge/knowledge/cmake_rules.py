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
    "generate_messages": "# removed: rosidl_generate_interfaces handles this",
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
    "image_transport": "image_transport",
    "cv_bridge": "cv_bridge",
    "rosbag": "rosbag2_cpp",
    "rosconsole": "rcutils",
    "rostest": "ament_cmake_gtest",
}

# CATKIN_PACKAGE_*_DESTINATION → ament install path
_DESTINATION_REMAP: dict[str, str] = {
    "CATKIN_GLOBAL_BIN_DESTINATION": "bin",
    "CATKIN_GLOBAL_LIB_DESTINATION": "lib",
    "CATKIN_PACKAGE_BIN_DESTINATION": "lib/${PROJECT_NAME}",
    "CATKIN_PACKAGE_LIB_DESTINATION": "lib",
    "CATKIN_PACKAGE_INCLUDE_DESTINATION": "include/${PROJECT_NAME}",
    "CATKIN_PACKAGE_SHARE_DESTINATION": "share/${PROJECT_NAME}",
}


def _remap_pkg(name: str) -> str:
    """Return the ROS2 name for a ROS1 package, or the original if unknown."""
    return _PKG_REMAP.get(name, name)


def _remap_destinations(line: str) -> str:
    """Replace CATKIN_*_DESTINATION variables with ament equivalents."""
    for ros1_dest, ros2_dest in _DESTINATION_REMAP.items():
        line = line.replace(f"${{{ros1_dest}}}", ros2_dest)
        line = line.replace(ros1_dest, ros2_dest)
    return line


def _is_generate_messages_block(line: str) -> bool:
    return bool(re.match(r"\s*generate_messages\s*\(", line))


def _is_add_message_files_block(line: str) -> bool:
    return bool(re.match(r"\s*add_message_files\s*\(", line))


def _is_add_service_files_block(line: str) -> bool:
    return bool(re.match(r"\s*add_service_files\s*\(", line))


def _is_catkin_python_setup(line: str) -> bool:
    return bool(re.match(r"\s*catkin_python_setup\s*\(", line))


def _consume_block(lines: list[str], start: int) -> tuple[str, int]:
    """Consume a parenthesized block starting at lines[start].

    Returns the full block text and the index of the closing-paren line.
    """
    block = lines[start]
    i = start
    depth = block.count("(") - block.count(")")
    while depth > 0 and i + 1 < len(lines):
        i += 1
        block += lines[i]
        depth += lines[i].count("(") - lines[i].count(")")
    return block, i


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

    # Track state
    ament_cmake_added = False
    ament_package_present = False
    # Collect rosidl blocks to merge into a single call
    msg_files: list[str] = []
    srv_files: list[str] = []
    rosidl_deps: list[str] = []
    # Lines to emit before ament_package()
    deferred_rosidl: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # ------------------------------------------------------------------ #
        # find_package(catkin REQUIRED COMPONENTS ...) → individual find_package
        # ------------------------------------------------------------------ #
        if re.match(r"\s*find_package\s*\(\s*catkin\b", line):
            block, i = _consume_block(lines, i)

            if not ament_cmake_added:
                output.append("find_package(ament_cmake REQUIRED)\n")
                ament_cmake_added = True
            for dep in ros2_deps:
                output.append(f"find_package({dep} REQUIRED)\n")
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # catkin_package(...) → ament_package() — defer to end of file
        # ------------------------------------------------------------------ #
        if re.match(r"\s*catkin_package\s*\(", line):
            block, i = _consume_block(lines, i)
            # Don't emit ament_package() here; defer to end to ensure it's last
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # catkin_python_setup() → ament_python_install_package(${PROJECT_NAME})
        # ------------------------------------------------------------------ #
        if _is_catkin_python_setup(line):
            block, i = _consume_block(lines, i)
            output.append("ament_python_install_package(${PROJECT_NAME})\n")
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # add_message_files(...) — collect for rosidl_generate_interfaces
        # ------------------------------------------------------------------ #
        if _is_add_message_files_block(line):
            block, i = _consume_block(lines, i)
            # Extract FILES entries
            files_match = re.findall(r"FILES\s+((?:\S+\.msg\s*)+)", block)
            for f_group in files_match:
                msg_files.extend(f_group.split())
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # add_service_files(...) — collect for rosidl_generate_interfaces
        # ------------------------------------------------------------------ #
        if _is_add_service_files_block(line):
            block, i = _consume_block(lines, i)
            files_match = re.findall(r"FILES\s+((?:\S+\.srv\s*)+)", block)
            for f_group in files_match:
                srv_files.extend(f_group.split())
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # generate_messages(...) — remove (replaced by rosidl_generate_interfaces)
        # ------------------------------------------------------------------ #
        if _is_generate_messages_block(line):
            block, i = _consume_block(lines, i)
            # Extract DEPENDENCIES to include in rosidl call
            dep_match = re.findall(r"DEPENDENCIES\s+((?:\S+\s*)+?)(?:\))", block)
            for d_group in dep_match:
                rosidl_deps.extend(d_group.split())
            i += 1
            continue

        # ------------------------------------------------------------------ #
        # include_directories(${catkin_INCLUDE_DIRS} ...)
        # → ament_target_dependencies(target deps...)
        # ------------------------------------------------------------------ #
        if re.match(r"\s*include_directories\s*\(", line) and "catkin_INCLUDE_DIRS" in line:
            block, i = _consume_block(lines, i)
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
            block, i = _consume_block(lines, i)
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
        line = line.replace("${catkin_EXPORTED_TARGETS}", "")

        # Remap CATKIN_*_DESTINATION variables
        line = _remap_destinations(line)

        # Remap package names that appear as plain tokens
        for ros1_pkg, ros2_pkg in _PKG_REMAP.items():
            if ros2_pkg:
                line = re.sub(rf"\b{re.escape(ros1_pkg)}\b", ros2_pkg, line)

        if "ament_package()" in line:
            ament_package_present = True

        output.append(line)
        i += 1

    # ------------------------------------------------------------------ #
    # Emit rosidl_generate_interfaces block if we collected msg/srv files
    # ------------------------------------------------------------------ #
    if msg_files or srv_files:
        rosidl_lines = ["rosidl_generate_interfaces(${PROJECT_NAME}\n"]
        for mf in msg_files:
            rosidl_lines.append(f'  "msg/{mf}"\n')
        for sf in srv_files:
            rosidl_lines.append(f'  "srv/{sf}"\n')
        if rosidl_deps:
            rosidl_lines.append(f"  DEPENDENCIES {' '.join(rosidl_deps)}\n")
        rosidl_lines.append(")\n")
        deferred_rosidl = rosidl_lines

    # ------------------------------------------------------------------ #
    # Ensure ament_package() is LAST
    # ------------------------------------------------------------------ #
    if ament_package_present:
        # Remove existing ament_package() lines and re-add at end
        output = [ln for ln in output if "ament_package()" not in ln]

    if deferred_rosidl:
        output.append("\n")
        output.extend(deferred_rosidl)

    output.append("\nament_package()\n")

    return "".join(output)
