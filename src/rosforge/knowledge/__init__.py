"""ROSForge knowledge base.

Static ROS1 → ROS2 mapping tables and rule-based transformers used by both
the PromptBuilder (injected into AI prompts) and the deterministic pipeline
stages.
"""

from rosforge.knowledge.api_mappings import (
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    get_mapping,
)
from rosforge.knowledge.cmake_rules import (
    CATKIN_TO_AMENT,
    transform_cmake,
)
from rosforge.knowledge.custom_rules import (
    CustomRules,
    load_custom_rules,
)
from rosforge.knowledge.launch_rules import (
    transform_launch_xml,
)
from rosforge.knowledge.msg_srv_rules import (
    transform_action,
    transform_msg,
    transform_srv,
)
from rosforge.knowledge.package_xml_rules import (
    ROS1_TO_ROS2_PACKAGES,
    normalize_format1_dependencies,
    transform_package_xml,
)


def merge_custom_rules(
    custom: CustomRules,
    cpp_base: dict[str, str],
    python_base: dict[str, str],
    package_base: dict[str, str],
    cmake_base: dict[str, str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    """Merge custom rules into built-in mapping dicts.

    Returns NEW merged dicts — the originals are never mutated.
    Custom rules override built-in entries on key collision.

    Args:
        custom: User-supplied :class:`CustomRules` loaded from YAML.
        cpp_base: Built-in roscpp → rclcpp mapping (e.g. ``ROSCPP_TO_RCLCPP``).
        python_base: Built-in rospy → rclpy mapping (e.g. ``ROSPY_TO_RCLPY``).
        package_base: Built-in package name mapping (e.g. ``ROS1_TO_ROS2_PACKAGES``).
        cmake_base: Built-in CMake keyword mapping (e.g. ``CATKIN_TO_AMENT``).

    Returns:
        A tuple ``(cpp, python, package, cmake)`` of merged dicts.
    """
    # Custom entries are placed FIRST so they appear within the 60-row cap
    # used by _format_mapping_table when injecting tables into prompts.
    # Built-in entries follow; on key collision the custom value wins because
    # the custom dict was merged first and the built-in update would overwrite
    # it — so we filter out colliding built-in keys instead.
    cpp = {
        **custom.cpp_mappings,
        **{k: v for k, v in cpp_base.items() if k not in custom.cpp_mappings},
    }
    python = {
        **custom.python_mappings,
        **{k: v for k, v in python_base.items() if k not in custom.python_mappings},
    }
    package = {
        **custom.package_mappings,
        **{k: v for k, v in package_base.items() if k not in custom.package_mappings},
    }
    cmake = {
        **custom.cmake_mappings,
        **{k: v for k, v in cmake_base.items() if k not in custom.cmake_mappings},
    }
    return cpp, python, package, cmake


__all__ = [
    "CATKIN_TO_AMENT",
    "ROS1_TO_ROS2_PACKAGES",
    "ROSCPP_TO_RCLCPP",
    "ROSPY_TO_RCLPY",
    "CustomRules",
    "get_mapping",
    "load_custom_rules",
    "merge_custom_rules",
    "normalize_format1_dependencies",
    "transform_action",
    "transform_cmake",
    "transform_launch_xml",
    "transform_msg",
    "transform_package_xml",
    "transform_srv",
]
