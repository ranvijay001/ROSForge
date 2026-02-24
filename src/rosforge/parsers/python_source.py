"""Scan Python source files for ROS1 API usage.

TODO(Phase 1): Implement full Python ROS1 API scanning.
Patterns to detect: import rospy, rospy.init_node, rospy.Publisher,
rospy.Subscriber, rospy.Service, rospy.ServiceProxy, rospy.get_param, etc.
"""

from __future__ import annotations

from pathlib import Path

from rosforge.models.ir import ROSAPIUsage


def scan_python(path: Path) -> list[ROSAPIUsage]:
    """Scan a Python source file for ROS1 API usage.

    TODO(Phase 1): Not yet implemented.
    """
    return []
