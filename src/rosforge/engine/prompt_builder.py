"""PromptBuilder — construct AI prompts from IR and knowledge base tables."""

from __future__ import annotations

import json

from rosforge.knowledge import (
    CATKIN_TO_AMENT,
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    ROS1_TO_ROS2_PACKAGES,
)
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import MigrationPlan

# Rough token budget (chars / 4).  Most models allow 128 k input tokens.
_CHARS_PER_TOKEN = 4
_MODEL_TOKEN_LIMIT = 128_000
_TOKEN_BUDGET = int(_MODEL_TOKEN_LIMIT * 0.80)  # 80 % of limit


def _format_mapping_table(mapping: dict[str, str], title: str) -> str:
    """Render a dict as a compact markdown table for prompt injection."""
    if not mapping:
        return ""
    lines = [f"### {title}", "| ROS 1 | ROS 2 |", "| --- | --- |"]
    for k, v in list(mapping.items())[:60]:  # cap at 60 rows to save tokens
        lines.append(f"| `{k}` | `{v}` |")
    return "\n".join(lines)


class PromptBuilder:
    """Build system/user prompt pairs for AI transform and analyze tasks."""

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

    def _truncate_if_needed(self, text: str, budget_tokens: int) -> str:
        """Strip trailing comment blocks if text would exceed budget."""
        if self.estimate_tokens(text) <= budget_tokens:
            return text
        # Truncate to fit; add notice
        max_chars = budget_tokens * _CHARS_PER_TOKEN
        return text[:max_chars] + "\n/* ... truncated to fit token budget ... */"

    # ------------------------------------------------------------------
    # Knowledge base injection
    # ------------------------------------------------------------------

    def _knowledge_section(self) -> str:
        cpp_table = _format_mapping_table(ROSCPP_TO_RCLCPP, "C++ API Mappings (roscpp → rclcpp)")
        py_table = _format_mapping_table(ROSPY_TO_RCLPY, "Python API Mappings (rospy → rclpy)")
        cmake_table = _format_mapping_table(CATKIN_TO_AMENT, "CMake Mappings (catkin → ament)")
        pkg_table = _format_mapping_table(ROS1_TO_ROS2_PACKAGES, "Package Name Mappings")
        parts = [s for s in [cpp_table, py_table, cmake_table, pkg_table] if s]
        return "\n\n".join(parts)

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

        Args:
            source_file: The source file to transform.
            plan: The migration plan for context.
            knowledge_base: Optional override (unused in Phase 0).

        Returns:
            (system_prompt, user_prompt) tuple of strings.
        """
        system_prompt = (
            "You are an expert ROS1-to-ROS2 migration engineer.\n"
            "Transform the provided ROS1 source file to its ROS2 equivalent.\n\n"
            "## Knowledge Base\n\n"
            + self._knowledge_section()
            + "\n\n"
            "## Output Format\n\n"
            "Return a single JSON object:\n"
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
