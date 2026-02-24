"""ROS1 → ROS2 message and service definition transformation rules.

TODO: Implement .msg / .srv / .action file transformations.
      Key areas to cover:
      - Header field type: Header → std_msgs/msg/Header
      - Built-in type renames (none in ROS2 for primitives)
      - Array syntax changes (none required)
      - Service/action package suffix conventions (_srv, _action)
      - rosidl_generate_interfaces CMake integration
"""

from __future__ import annotations


def transform_msg(original: str) -> str:
    """Transform a ROS1 .msg file to ROS2 format.

    TODO: Implement.
    """
    raise NotImplementedError("msg_srv_rules.transform_msg is not yet implemented")


def transform_srv(original: str) -> str:
    """Transform a ROS1 .srv file to ROS2 format.

    TODO: Implement.
    """
    raise NotImplementedError("msg_srv_rules.transform_srv is not yet implemented")


def transform_action(original: str) -> str:
    """Transform a ROS1 .action file to ROS2 format.

    TODO: Implement.
    """
    raise NotImplementedError("msg_srv_rules.transform_action is not yet implemented")
