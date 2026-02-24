"""Parse ROS1 .msg and .srv definition files.

TODO(Phase 1): Implement full message/service definition parsing.
For .msg: extract field types, field names, constants.
For .srv: split request/response sections on '---' delimiter.
"""

from __future__ import annotations

from pathlib import Path


def parse_msg_srv(path: Path) -> dict:
    """Parse a ROS1 .msg or .srv definition file.

    TODO(Phase 1): Not yet implemented.
    """
    return {}
