"""PromptBuilder — construct AI prompts from IR and knowledge base tables."""

from __future__ import annotations

import json

from rosforge.knowledge import (
    CATKIN_TO_AMENT,
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    ROS1_TO_ROS2_PACKAGES,
    merge_custom_rules,
)
from rosforge.knowledge.custom_rules import CustomRules
from rosforge.models.ir import FileType, PackageIR, SourceFile
from rosforge.models.plan import MigrationPlan

# Rough token budget (chars / 4).  Most models allow 128 k input tokens.
_CHARS_PER_TOKEN = 4
_MODEL_TOKEN_LIMIT = 128_000
_TOKEN_BUDGET = int(_MODEL_TOKEN_LIMIT * 0.80)  # 80 % of limit

# Per-backend output format hints
_FORMAT_API = "json"       # structured JSON response
_FORMAT_CLI = "markdown"   # markdown with fenced JSON block


def _format_mapping_table(mapping: dict[str, str], title: str) -> str:
    """Render a dict as a compact markdown table for prompt injection."""
    if not mapping:
        return ""
    lines = [f"### {title}", "| ROS 1 | ROS 2 |", "| --- | --- |"]
    for k, v in list(mapping.items())[:60]:  # cap at 60 rows to save tokens
        lines.append(f"| `{k}` | `{v}` |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-file-type system prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_CPP = """\
You are an expert C++ ROS1-to-ROS2 migration engineer.
Transform the provided roscpp source file to its rclcpp equivalent.
Key rules:
- Replace #include "ros/ros.h" with #include "rclcpp/rclcpp.hpp"
- Replace ros::NodeHandle with rclcpp::Node
- Replace ros::Publisher/Subscriber with rclcpp Publisher/Subscription SharedPtrs
- Replace ROS_INFO/WARN/ERROR macros with RCLCPP_ equivalents using node->get_logger()
- Replace ros::spin() with rclcpp::spin(node)
- Replace ros::Time::now() with node->now()
- Use node->create_publisher / create_subscription instead of nh.advertise / nh.subscribe
"""

_SYSTEM_PYTHON = """\
You are an expert Python ROS1-to-ROS2 migration engineer.
Transform the provided rospy script to its rclpy equivalent.
Key rules:
- Replace import rospy with import rclpy
- Replace rospy.init_node with rclpy.init() + node = rclpy.create_node()
- Replace rospy.Publisher/Subscriber with node.create_publisher/create_subscription
- Replace rospy.loginfo/warn/err with node.get_logger().info/warn/error
- Replace rospy.spin() with rclpy.spin(node)
- Replace rospy.Rate with node.create_rate
- Replace rospy.get_param with node.get_parameter
"""

_SYSTEM_LAUNCH = """\
You are an expert ROS1-to-ROS2 launch file migration engineer.
Convert the provided roslaunch XML file to a Python launch file (ROS2 style).
Key rules:
- Output must be a Python file, not XML
- Use from launch import LaunchDescription
- Use from launch_ros.actions import Node
- Map <node> tags to Node() actions
- Map <include> tags to IncludeLaunchDescription
- Map <arg> tags to DeclareLaunchArgument
- Map <param> tags to node parameters dict
- Map <remap> tags to node remappings list
"""

_SYSTEM_CMAKE = """\
You are an expert CMake ROS1-to-ROS2 migration engineer.
Transform the provided CMakeLists.txt from catkin to ament_cmake.
Key rules:
- Replace find_package(catkin REQUIRED COMPONENTS ...) with individual find_package calls
- Replace catkin_package() with ament_package()
- Replace catkin_build with ament_cmake build macros
- Replace include_directories(${catkin_INCLUDE_DIRS}) with target_include_directories
- Replace target_link_libraries(...${catkin_LIBRARIES}) with ament_target_dependencies
- Add ament_target_dependencies() calls for ROS2 packages
"""

_SYSTEM_GENERIC = """\
You are an expert ROS1-to-ROS2 migration engineer.
Transform the provided ROS1 source file to its ROS2 equivalent.
Apply all necessary changes to make the file compatible with ROS2 (Humble or later).
"""

_FILE_TYPE_SYSTEM_PROMPTS: dict[FileType, str] = {
    FileType.CPP: _SYSTEM_CPP,
    FileType.HPP: _SYSTEM_CPP,
    FileType.PYTHON: _SYSTEM_PYTHON,
    FileType.LAUNCH_XML: _SYSTEM_LAUNCH,
    FileType.CMAKE: _SYSTEM_CMAKE,
}

# Output format instructions per backend
_OUTPUT_FORMAT_API = (
    "Return ONLY a valid JSON object with no additional text:\n"
    "```json\n"
    "{\n"
    '  "source_path": "string",\n'
    '  "target_path": "string",\n'
    '  "transformed_content": "string",\n'
    '  "confidence": 0.0,\n'
    '  "strategy_used": "ai_driven",\n'
    '  "warnings": ["string"],\n'
    '  "changes": [\n'
    '    {"description": "string", "line_range": "string", "reason": "string"}\n'
    "  ]\n"
    "}\n"
    "```"
)

_OUTPUT_FORMAT_CLI = (
    "Return your response as a markdown code block containing a JSON object:\n"
    "```json\n"
    "{\n"
    '  "source_path": "string",\n'
    '  "target_path": "string",\n'
    '  "transformed_content": "string",\n'
    '  "confidence": 0.0,\n'
    '  "strategy_used": "ai_driven",\n'
    '  "warnings": ["string"],\n'
    '  "changes": [\n'
    '    {"description": "string", "line_range": "string", "reason": "string"}\n'
    "  ]\n"
    "}\n"
    "```"
)


class PromptBuilder:
    """Build system/user prompt pairs for AI transform and analyze tasks."""

    def __init__(
        self,
        backend_mode: str = "api",
        custom_rules: CustomRules | None = None,
    ) -> None:
        """Initialise the PromptBuilder.

        Args:
            backend_mode: Either ``"api"`` (structured JSON response expected)
                          or ``"cli"`` (markdown fenced block expected).
            custom_rules: Optional user-supplied mapping overrides.  When
                provided, custom entries are merged on top of the built-in
                knowledge tables (custom rules win on collision).
        """
        self._backend_mode = backend_mode
        self._custom_rules = custom_rules

        # Pre-compute merged mapping tables (never mutates module-level globals)
        if custom_rules is not None:
            (
                self._roscpp_to_rclcpp,
                self._rospy_to_rclpy,
                self._ros1_to_ros2_packages,
                self._catkin_to_ament,
            ) = merge_custom_rules(
                custom_rules,
                ROSCPP_TO_RCLCPP,
                ROSPY_TO_RCLPY,
                ROS1_TO_ROS2_PACKAGES,
                CATKIN_TO_AMENT,
            )
        else:
            self._roscpp_to_rclcpp = ROSCPP_TO_RCLCPP
            self._rospy_to_rclpy = ROSPY_TO_RCLPY
            self._ros1_to_ros2_packages = ROS1_TO_ROS2_PACKAGES
            self._catkin_to_ament = CATKIN_TO_AMENT

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimation: characters / 4.

        Args:
            text: Any string.

        Returns:
            Estimated token count.
        """
        return max(0, len(text) // _CHARS_PER_TOKEN)

    @staticmethod
    def estimate_file_tokens(file: SourceFile) -> int:
        """Estimate tokens required to include a source file in a prompt.

        Accounts for file content plus per-file overhead (path header, fences).

        Args:
            file: SourceFile with content populated.

        Returns:
            Estimated token count.
        """
        overhead = 50  # path header, code fences, etc.
        return max(0, len(file.content) // _CHARS_PER_TOKEN) + overhead

    def _truncate_if_needed(self, text: str, budget_tokens: int) -> str:
        """Strip trailing content if text would exceed budget."""
        if self.estimate_tokens(text) <= budget_tokens:
            return text
        max_chars = budget_tokens * _CHARS_PER_TOKEN
        return text[:max_chars] + "\n/* ... truncated to fit token budget ... */"

    # ------------------------------------------------------------------
    # Knowledge base injection
    # ------------------------------------------------------------------

    def _knowledge_section(self) -> str:
        cpp_table = _format_mapping_table(self._roscpp_to_rclcpp, "C++ API Mappings (roscpp → rclcpp)")
        py_table = _format_mapping_table(self._rospy_to_rclpy, "Python API Mappings (rospy → rclpy)")
        cmake_table = _format_mapping_table(self._catkin_to_ament, "CMake Mappings (catkin → ament)")
        pkg_table = _format_mapping_table(self._ros1_to_ros2_packages, "Package Name Mappings")
        parts = [s for s in [cpp_table, py_table, cmake_table, pkg_table] if s]
        return "\n\n".join(parts)

    def _knowledge_section_for_type(self, file_type: FileType) -> str:
        """Return a knowledge section relevant to the given file type."""
        if file_type in (FileType.CPP, FileType.HPP):
            cpp_table = _format_mapping_table(
                self._roscpp_to_rclcpp, "C++ API Mappings (roscpp → rclcpp)"
            )
            pkg_table = _format_mapping_table(self._ros1_to_ros2_packages, "Package Name Mappings")
            return "\n\n".join(filter(None, [cpp_table, pkg_table]))

        if file_type == FileType.PYTHON:
            py_table = _format_mapping_table(
                self._rospy_to_rclpy, "Python API Mappings (rospy → rclpy)"
            )
            pkg_table = _format_mapping_table(self._ros1_to_ros2_packages, "Package Name Mappings")
            return "\n\n".join(filter(None, [py_table, pkg_table]))

        if file_type == FileType.CMAKE:
            cmake_table = _format_mapping_table(
                self._catkin_to_ament, "CMake Mappings (catkin → ament)"
            )
            return cmake_table

        # Default: include all tables
        return self._knowledge_section()

    # ------------------------------------------------------------------
    # Output format helper
    # ------------------------------------------------------------------

    def _output_format_instructions(self) -> str:
        if self._backend_mode == "api":
            return _OUTPUT_FORMAT_API
        return _OUTPUT_FORMAT_CLI

    # ------------------------------------------------------------------
    # Analyze prompts
    # ------------------------------------------------------------------

    def build_analyze_prompt(self, package_ir: PackageIR) -> tuple[str, str]:
        """Build prompts for the Analyze stage.

        Args:
            package_ir: Parsed IR of the ROS1 package.

        Returns:
            (system_prompt, user_prompt) tuple of strings.
        """
        system_prompt = (
            "You are an expert ROS1-to-ROS2 migration engineer.\n"
            "Analyse the provided ROS1 package intermediate representation and "
            "return a JSON migration plan.\n\n"
            "## Knowledge Base\n\n"
            + self._knowledge_section()
            + "\n\n"
            "## Output Format\n\n"
            "Return a single JSON object matching this schema:\n"
            "```json\n"
            "{\n"
            '  "package_name": "string",\n'
            '  "target_ros2_distro": "humble",\n'
            '  "overall_confidence": 0.0,\n'
            '  "summary": "string",\n'
            '  "warnings": ["string"],\n'
            '  "actions": [\n'
            "    {\n"
            '      "source_path": "string",\n'
            '      "target_path": "string",\n'
            '      "strategy": "rule_based|ai_driven|skip|manual",\n'
            '      "description": "string",\n'
            '      "estimated_complexity": 1,\n'
            '      "confidence": 0.0\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "```"
        )

        pkg_summary = json.dumps(
            {
                "name": package_ir.metadata.name,
                "version": package_ir.metadata.version,
                "total_files": package_ir.total_files,
                "total_lines": package_ir.total_lines,
                "cpp_files": package_ir.cpp_files,
                "python_files": package_ir.python_files,
                "launch_files": package_ir.launch_files,
                "msg_srv_files": package_ir.msg_srv_files,
                "dependencies": [
                    {"name": d.name, "type": d.dep_type}
                    for d in package_ir.dependencies
                ],
                "api_usages": [
                    {"api": u.api_name, "file": u.file_path}
                    for u in package_ir.api_usages[:50]
                ],
            },
            indent=2,
        )

        user_prompt = (
            f"Analyse this ROS1 package and produce a migration plan.\n\n"
            f"## Package IR\n\n```json\n{pkg_summary}\n```"
        )

        return system_prompt, user_prompt

    # ------------------------------------------------------------------
    # Transform prompts
    # ------------------------------------------------------------------

    def build_transform_prompt(
        self,
        source_file: SourceFile,
        plan: MigrationPlan,
        knowledge_base: object | None = None,  # reserved for future override
    ) -> tuple[str, str]:
        """Build prompts for the Transform stage (single file).

        Selects a per-file-type system prompt and injects only the relevant
        knowledge base tables to minimise token usage.

        Args:
            source_file: The source file to transform.
            plan: The migration plan for context.
            knowledge_base: Optional override (unused in Phase 0).

        Returns:
            (system_prompt, user_prompt) tuple of strings.
        """
        # Per-file-type system prompt
        base_system = _FILE_TYPE_SYSTEM_PROMPTS.get(source_file.file_type, _SYSTEM_GENERIC)
        knowledge = self._knowledge_section_for_type(source_file.file_type)
        output_format = self._output_format_instructions()

        system_prompt = (
            base_system
            + "\n\n## Knowledge Base\n\n"
            + knowledge
            + "\n\n## Output Format\n\n"
            + output_format
        )

        # Find the action for this file
        action = next(
            (a for a in plan.actions if a.source_path == source_file.relative_path),
            None,
        )
        action_hint = (
            f"Strategy: {action.strategy}, complexity: {action.estimated_complexity}"
            if action
            else "No specific action found — use best judgement."
        )

        # Estimate remaining token budget for file content
        system_tokens = self.estimate_tokens(system_prompt)
        budget = _TOKEN_BUDGET - system_tokens - 500  # 500 token overhead
        content = self._truncate_if_needed(source_file.content, budget)

        user_prompt = (
            f"Transform this ROS1 file to ROS2.\n\n"
            f"File: `{source_file.relative_path}` ({source_file.file_type})\n"
            f"Migration hint: {action_hint}\n\n"
            f"## Source Content\n\n```\n{content}\n```"
        )

        return system_prompt, user_prompt

    # ------------------------------------------------------------------
    # Fix prompt (used by ValidateFixLoopStage)
    # ------------------------------------------------------------------

    def build_fix_prompt(
        self,
        source_file: SourceFile,
        transformed_content: str,
        error_message: str,
    ) -> tuple[str, str]:
        """Build prompts for fixing a failed or low-confidence transformation.

        Used by the fix loop (ValidateFixLoopStage) where the AI
        is asked to correct its own output after validation failures.

        Args:
            source_file: The original source file.
            transformed_content: The previously transformed (broken) content.
            error_message: The error or validation failure message.

        Returns:
            (system_prompt, user_prompt) tuple of strings.
        """
        base_system = _FILE_TYPE_SYSTEM_PROMPTS.get(source_file.file_type, _SYSTEM_GENERIC)
        output_format = self._output_format_instructions()

        system_prompt = (
            base_system
            + "\n\nYou previously transformed a ROS1 file but the result had issues. "
            "Fix the problems described below and return the corrected transformation.\n\n"
            "## Output Format\n\n"
            + output_format
        )

        system_tokens = self.estimate_tokens(system_prompt)
        budget = (_TOKEN_BUDGET - system_tokens - 500) // 2  # split budget between original and transformed
        original = self._truncate_if_needed(source_file.content, budget)
        transformed = self._truncate_if_needed(transformed_content, budget)

        user_prompt = (
            f"Fix the transformation for: `{source_file.relative_path}`\n\n"
            f"## Error / Validation Failure\n\n{error_message}\n\n"
            f"## Original ROS1 Source\n\n```\n{original}\n```\n\n"
            f"## Previous (Broken) ROS2 Output\n\n```\n{transformed}\n```\n\n"
            "Return the corrected transformation."
        )

        return system_prompt, user_prompt
