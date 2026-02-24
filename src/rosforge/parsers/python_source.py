"""Scan Python source files for ROS1 API usage."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from rosforge.models.ir import ROSAPIUsage

logger = logging.getLogger(__name__)

# Each entry: (api_name, compiled_regex)
_ROS1_PATTERNS: list[tuple[str, re.Pattern]] = [
    # imports
    ("rospy.import", re.compile(r"\bimport\s+rospy\b")),
    ("rospy.from_import", re.compile(r"\bfrom\s+rospy\b")),
    # node lifecycle
    ("rospy.init_node", re.compile(r"\brospy\.init_node\s*\(")),
    ("rospy.spin", re.compile(r"\brospy\.spin\s*\(")),
    ("rospy.is_shutdown", re.compile(r"\brospy\.is_shutdown\s*\(")),
    ("rospy.signal_shutdown", re.compile(r"\brospy\.signal_shutdown\s*\(")),
    ("rospy.on_shutdown", re.compile(r"\brospy\.on_shutdown\s*\(")),
    # pub/sub
    ("rospy.Publisher", re.compile(r"\brospy\.Publisher\s*\(")),
    ("rospy.Subscriber", re.compile(r"\brospy\.Subscriber\s*\(")),
    # services
    ("rospy.Service", re.compile(r"\brospy\.Service\s*\(")),
    ("rospy.ServiceProxy", re.compile(r"\brospy\.ServiceProxy\s*\(")),
    ("rospy.wait_for_service", re.compile(r"\brospy\.wait_for_service\s*\(")),
    # params
    ("rospy.get_param", re.compile(r"\brospy\.get_param\s*\(")),
    ("rospy.set_param", re.compile(r"\brospy\.set_param\s*\(")),
    ("rospy.has_param", re.compile(r"\brospy\.has_param\s*\(")),
    ("rospy.delete_param", re.compile(r"\brospy\.delete_param\s*\(")),
    ("rospy.search_param", re.compile(r"\brospy\.search_param\s*\(")),
    # names / namespace
    ("rospy.get_name", re.compile(r"\brospy\.get_name\s*\(")),
    ("rospy.get_namespace", re.compile(r"\brospy\.get_namespace\s*\(")),
    ("rospy.resolve_name", re.compile(r"\brospy\.resolve_name\s*\(")),
    # time
    ("rospy.Time", re.compile(r"\brospy\.Time\b")),
    ("rospy.Duration", re.compile(r"\brospy\.Duration\b")),
    ("rospy.Rate", re.compile(r"\brospy\.Rate\s*\(")),
    ("rospy.get_time", re.compile(r"\brospy\.get_time\s*\(")),
    ("rospy.get_rostime", re.compile(r"\brospy\.get_rostime\s*\(")),
    ("rospy.sleep", re.compile(r"\brospy\.sleep\s*\(")),
    # logging
    ("rospy.logdebug", re.compile(r"\brospy\.logdebug\s*\(")),
    ("rospy.loginfo", re.compile(r"\brospy\.loginfo\s*\(")),
    ("rospy.logwarn", re.compile(r"\brospy\.logwarn\s*\(")),
    ("rospy.logerr", re.compile(r"\brospy\.logerr\s*\(")),
    ("rospy.logfatal", re.compile(r"\brospy\.logfatal\s*\(")),
    # throttled / once logging variants
    ("rospy.logdebug_throttle", re.compile(r"\brospy\.logdebug_throttle\s*\(")),
    ("rospy.loginfo_throttle", re.compile(r"\brospy\.loginfo_throttle\s*\(")),
    ("rospy.logwarn_throttle", re.compile(r"\brospy\.logwarn_throttle\s*\(")),
    ("rospy.logerr_throttle", re.compile(r"\brospy\.logerr_throttle\s*\(")),
    ("rospy.logdebug_once", re.compile(r"\brospy\.logdebug_once\s*\(")),
    ("rospy.loginfo_once", re.compile(r"\brospy\.loginfo_once\s*\(")),
    ("rospy.logwarn_once", re.compile(r"\brospy\.logwarn_once\s*\(")),
    ("rospy.logerr_once", re.compile(r"\brospy\.logerr_once\s*\(")),
    # exceptions / misc
    ("rospy.ROSException", re.compile(r"\brospy\.ROSException\b")),
    ("rospy.ROSInterruptException", re.compile(r"\brospy\.ROSInterruptException\b")),
    ("rospy.AnyMsg", re.compile(r"\brospy\.AnyMsg\b")),
    ("rospy.Header", re.compile(r"\brospy\.Header\b")),
    ("rospy.myargv", re.compile(r"\brospy\.myargv\s*\(")),
    # action lib (actionlib is separate but commonly used with rospy)
    ("actionlib.SimpleActionClient", re.compile(r"\bactionlib\.SimpleActionClient\s*\(")),
    ("actionlib.SimpleActionServer", re.compile(r"\bactionlib\.SimpleActionServer\s*\(")),
]


def scan_python(path: Path) -> list[ROSAPIUsage]:
    """Scan a Python source file for ROS1 API usage.

    Args:
        path: Path to .py file

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
