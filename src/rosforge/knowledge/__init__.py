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

__all__ = [
    # api_mappings
    "ROSCPP_TO_RCLCPP",
    "ROSPY_TO_RCLPY",
    "get_mapping",
    # cmake_rules
    "CATKIN_TO_AMENT",
    "transform_cmake",
    # launch_rules
    "transform_launch_xml",
    # msg_srv_rules
    "transform_msg",
    "transform_srv",
    "transform_action",
    # package_xml_rules
    "ROS1_TO_ROS2_PACKAGES",
    "normalize_format1_dependencies",
    "transform_package_xml",
]
