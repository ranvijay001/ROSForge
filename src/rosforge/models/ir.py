"""Intermediate Representation for a ROS1 package.

PackageIR is the central data structure produced by the Ingest stage.
It captures everything ROSForge knows about a ROS1 package after parsing.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Source file classification."""

    CPP = "cpp"
    HPP = "hpp"
    PYTHON = "python"
    LAUNCH_XML = "launch_xml"
    MSG = "msg"
    SRV = "srv"
    ACTION = "action"
    CMAKE = "cmake"
    PACKAGE_XML = "package_xml"
    OTHER = "other"


class DependencyType(str, Enum):
    """ROS dependency categories in package.xml."""

    BUILD = "build_depend"
    BUILD_EXPORT = "build_export_depend"
    EXEC = "exec_depend"
    BUILDTOOL = "buildtool_depend"
    DEPEND = "depend"  # shorthand for build + exec
    TEST = "test_depend"


class ROSAPIUsage(BaseModel):
    """A detected ROS API call in source code."""

    api_name: str  # e.g. "ros::NodeHandle::subscribe"
    file_path: str
    line_number: int = 0
    pattern: str = ""  # the regex/pattern that matched


class Dependency(BaseModel):
    """A single package dependency."""

    name: str
    dep_type: DependencyType
    version_gte: str | None = None
    version_lte: str | None = None
    condition: str | None = None  # e.g. "$ROS_DISTRO == noetic"


class SourceFile(BaseModel):
    """A single file within the ROS1 package."""

    relative_path: str  # relative to package root
    file_type: FileType
    content: str = ""
    line_count: int = 0
    api_usages: list[ROSAPIUsage] = Field(default_factory=list)
    encoding: str = "utf-8"


class PackageMetadata(BaseModel):
    """Parsed package.xml metadata."""

    name: str = ""
    version: str = "0.0.0"
    description: str = ""
    format_version: int = 2  # package.xml format="N"
    maintainers: list[str] = Field(default_factory=list)
    licenses: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    build_type: str = "catkin"  # catkin or cmake


class PackageIR(BaseModel):
    """Complete intermediate representation of a ROS1 package.

    Produced by the Ingest stage, consumed by Analyze and Transform.
    """

    source_path: Path
    metadata: PackageMetadata = Field(default_factory=PackageMetadata)
    dependencies: list[Dependency] = Field(default_factory=list)
    source_files: list[SourceFile] = Field(default_factory=list)
    api_usages: list[ROSAPIUsage] = Field(default_factory=list)

    # Summary stats for cost estimation
    total_lines: int = 0
    total_files: int = 0
    cpp_files: int = 0
    python_files: int = 0
    launch_files: int = 0
    msg_srv_files: int = 0

    def get_files_by_type(self, file_type: FileType) -> list[SourceFile]:
        """Filter source files by type."""
        return [f for f in self.source_files if f.file_type == file_type]
