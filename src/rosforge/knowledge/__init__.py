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
from rosforge.knowledge.package_xml_rules import (
    ROS1_TO_ROS2_PACKAGES,
    transform_package_xml,
)

__all__ = [
    # api_mappings
    "ROSCPP_TO_RCLCPP",
    "ROSPY_TO_RCLPY",
    "get_mapping",
    # cmake_rules
    "CATKIN_TO_AMENT",
    "transform_cmake",
    # package_xml_rules
    "ROS1_TO_ROS2_PACKAGES",
    "transform_package_xml",
]
