"""Scan C++ source files for ROS1 API usage patterns."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from rosforge.models.ir import ROSAPIUsage

logger = logging.getLogger(__name__)

# Each entry: (api_name, compiled_regex)
_ROS1_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ros::include", re.compile(r'#\s*include\s*[<"]\s*ros/ros\.h\s*[>"]')),
    ("ros::init", re.compile(r'\bros::init\s*\(')),
    ("ros::NodeHandle", re.compile(r'\bros::NodeHandle\b')),
    ("ros::Publisher", re.compile(r'\bros::Publisher\b')),
    ("ros::Subscriber", re.compile(r'\bros::Subscriber\b')),
    ("ros::ServiceServer", re.compile(r'\bros::ServiceServer\b')),
    ("ros::ServiceClient", re.compile(r'\bros::ServiceClient\b')),
    ("ros::Rate", re.compile(r'\bros::Rate\b')),
    ("ros::spin", re.compile(r'\bros::spin\s*\(')),
    ("ros::spinOnce", re.compile(r'\bros::spinOnce\s*\(')),
    ("ros::ok", re.compile(r'\bros::ok\s*\(')),
    ("ros::shutdown", re.compile(r'\bros::shutdown\s*\(')),
    ("ros::Time", re.compile(r'\bros::Time\b')),
    ("ros::Duration", re.compile(r'\bros::Duration\b')),
    ("ros::param", re.compile(r'\bros::param\s*::')),
    ("nh.advertise", re.compile(r'\b\w+\.advertise\s*<')),
    ("nh.subscribe", re.compile(r'\b\w+\.subscribe\s*\(')),
    ("nh.advertiseService", re.compile(r'\b\w+\.advertiseService\s*\(')),
    ("nh.serviceClient", re.compile(r'\b\w+\.serviceClient\s*<')),
    ("nh.getParam", re.compile(r'\b\w+\.getParam\s*\(')),
    ("nh.setParam", re.compile(r'\b\w+\.setParam\s*\(')),
    ("nh.param", re.compile(r'\b\w+\.param\s*\(')),
    ("ROS_INFO", re.compile(r'\bROS_INFO(?:_NAMED|_STREAM|_STREAM_NAMED|_ONCE|_THROTTLE)?\s*\(')),
    ("ROS_WARN", re.compile(r'\bROS_WARN(?:_NAMED|_STREAM|_STREAM_NAMED|_ONCE|_THROTTLE)?\s*\(')),
    ("ROS_ERROR", re.compile(r'\bROS_ERROR(?:_NAMED|_STREAM|_STREAM_NAMED|_ONCE|_THROTTLE)?\s*\(')),
    ("ROS_DEBUG", re.compile(r'\bROS_DEBUG(?:_NAMED|_STREAM|_STREAM_NAMED|_ONCE|_THROTTLE)?\s*\(')),
    ("ROS_FATAL", re.compile(r'\bROS_FATAL(?:_NAMED|_STREAM|_STREAM_NAMED)?\s*\(')),
    ("ROS_ASSERT", re.compile(r'\bROS_ASSERT\s*\(')),
]


def scan_cpp(path: Path) -> list[ROSAPIUsage]:
    """Scan a C++ source file for ROS1 API usage.

    Args:
        path: Path to .cpp or .hpp file

    Returns:
        List of ROSAPIUsage instances, one per matched line per pattern.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return []

    lines = text.splitlines()
    usages: list[ROSAPIUsage] = []
    file_str = str(path)

    for api_name, pattern in _ROS1_PATTERNS:
        for lineno, line in enumerate(lines, start=1):
            if pattern.search(line):
                usages.append(
                    ROSAPIUsage(
                        api_name=api_name,
                        file_path=file_str,
                        line_number=lineno,
                        pattern=pattern.pattern,
                    )
                )

    return usages
