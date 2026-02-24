"""Unit tests for custom_rules YAML loader and merge utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.knowledge import (
    CATKIN_TO_AMENT,
    ROS1_TO_ROS2_PACKAGES,
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    merge_custom_rules,
)
from rosforge.knowledge.custom_rules import CustomRules, load_custom_rules
from rosforge.models.ir import FileType, SourceFile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FULL_YAML = """\
version: 1
api_mappings:
  cpp:
    "old::Api": "new::Api"
    "old::Other": "new::Other"
  python:
    "old_module.func": "new_module.func"
package_mappings:
  old_pkg: new_pkg
cmake_mappings:
  "find_package(old_pkg)": "find_package(new_pkg)"
"""

_MINIMAL_YAML = "version: 1\n"


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "custom_rules.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _make_source_file(
    path: str = "src/node.cpp",
    file_type: FileType = FileType.CPP,
    content: str = "#include <ros/ros.h>\nint main() {}",
) -> SourceFile:
    return SourceFile(
        relative_path=path,
        file_type=file_type,
        content=content,
        line_count=content.count("\n") + 1,
    )


# ---------------------------------------------------------------------------
# load_custom_rules
# ---------------------------------------------------------------------------


class TestLoadValidYaml:
    def test_returns_custom_rules_instance(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, _FULL_YAML)
        result = load_custom_rules(p)
        assert isinstance(result, CustomRules)

    def test_cpp_mappings_populated(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, _FULL_YAML)
        result = load_custom_rules(p)
        assert result.cpp_mappings == {"old::Api": "new::Api", "old::Other": "new::Other"}

    def test_python_mappings_populated(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, _FULL_YAML)
        result = load_custom_rules(p)
        assert result.python_mappings == {"old_module.func": "new_module.func"}

    def test_package_mappings_populated(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, _FULL_YAML)
        result = load_custom_rules(p)
        assert result.package_mappings == {"old_pkg": "new_pkg"}

    def test_cmake_mappings_populated(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, _FULL_YAML)
        result = load_custom_rules(p)
        assert result.cmake_mappings == {"find_package(old_pkg)": "find_package(new_pkg)"}


class TestLoadMinimalYaml:
    def test_only_version_key_returns_empty_dicts(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, _MINIMAL_YAML)
        result = load_custom_rules(p)
        assert result.cpp_mappings == {}
        assert result.python_mappings == {}
        assert result.package_mappings == {}
        assert result.cmake_mappings == {}


class TestLoadMissingFile:
    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="nonexistent.yaml"):
            load_custom_rules(missing)


class TestLoadInvalidYaml:
    def test_raises_value_error_on_bad_yaml(self, tmp_path: Path) -> None:
        bad_yaml = "version: 1\napi_mappings: [\nunot closed"
        p = _write_yaml(tmp_path, bad_yaml)
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_custom_rules(p)

    def test_raises_value_error_on_non_mapping_top_level(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, "- item1\n- item2\n")
        with pytest.raises(ValueError):
            load_custom_rules(p)


class TestLoadBadVersion:
    def test_raises_value_error_for_version_2(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, "version: 2\n")
        with pytest.raises(ValueError, match="Unsupported custom rules version"):
            load_custom_rules(p)

    def test_raises_value_error_for_missing_version(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, "api_mappings:\n  cpp:\n    a: b\n")
        with pytest.raises(ValueError, match="Unsupported custom rules version"):
            load_custom_rules(p)

    def test_raises_value_error_for_string_version(self, tmp_path: Path) -> None:
        p = _write_yaml(tmp_path, 'version: "1"\n')
        with pytest.raises(ValueError, match="Unsupported custom rules version"):
            load_custom_rules(p)


# ---------------------------------------------------------------------------
# merge_custom_rules
# ---------------------------------------------------------------------------


class TestMergeOverridesBuiltin:
    def test_custom_cpp_overrides_builtin(self) -> None:
        custom = CustomRules(cpp_mappings={"ros::init": "MY_CUSTOM_INIT"})
        cpp, _, _, _ = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        assert cpp["ros::init"] == "MY_CUSTOM_INIT"

    def test_custom_python_overrides_builtin(self) -> None:
        custom = CustomRules(python_mappings={"rospy.init_node": "MY_INIT"})
        _, python, _, _ = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        assert python["rospy.init_node"] == "MY_INIT"

    def test_custom_package_overrides_builtin(self) -> None:
        custom = CustomRules(package_mappings={"roscpp": "MY_RCLCPP"})
        _, _, package, _ = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        assert package["roscpp"] == "MY_RCLCPP"

    def test_custom_cmake_overrides_builtin(self) -> None:
        custom = CustomRules(cmake_mappings={"catkin_package": "MY_AMENT_PKG"})
        _, _, _, cmake = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        assert cmake["catkin_package"] == "MY_AMENT_PKG"


class TestMergePreservesBuiltin:
    def test_builtin_globals_not_mutated(self) -> None:
        original_cpp_value = ROSCPP_TO_RCLCPP.get("ros::init")
        custom = CustomRules(cpp_mappings={"ros::init": "OVERRIDE"})
        merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        # Global must remain unchanged
        assert ROSCPP_TO_RCLCPP.get("ros::init") == original_cpp_value

    def test_builtin_entries_present_in_merged_result(self) -> None:
        custom = CustomRules(cpp_mappings={"brand::New": "brand::New2"})
        cpp, _, _, _ = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        # All original builtin keys must still be present
        for k, v in ROSCPP_TO_RCLCPP.items():
            assert cpp[k] == v

    def test_custom_new_key_added(self) -> None:
        custom = CustomRules(cpp_mappings={"brand_new::Api": "brand_new::Api2"})
        cpp, _, _, _ = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        assert cpp["brand_new::Api"] == "brand_new::Api2"

    def test_empty_custom_rules_returns_copy_of_builtins(self) -> None:
        custom = CustomRules()
        cpp, python, package, cmake = merge_custom_rules(
            custom, ROSCPP_TO_RCLCPP, ROSPY_TO_RCLPY, ROS1_TO_ROS2_PACKAGES, CATKIN_TO_AMENT
        )
        assert cpp == ROSCPP_TO_RCLCPP
        assert python == ROSPY_TO_RCLPY
        assert package == ROS1_TO_ROS2_PACKAGES
        assert cmake == CATKIN_TO_AMENT
        # Returned dicts are new objects (not the same references)
        assert cpp is not ROSCPP_TO_RCLCPP


# ---------------------------------------------------------------------------
# PromptBuilder with custom_rules
# ---------------------------------------------------------------------------


class TestPromptBuilderIncludesCustom:
    def test_custom_cpp_mapping_appears_in_cpp_system_prompt(self) -> None:
        custom = CustomRules(cpp_mappings={"my_custom::Old": "my_custom::New"})
        pb = PromptBuilder(custom_rules=custom)
        f = _make_source_file("src/node.cpp", FileType.CPP)
        from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy

        plan = MigrationPlan(
            package_name="test_pkg",
            actions=[
                TransformAction(
                    source_path="src/node.cpp",
                    target_path="src/node.cpp",
                    strategy=TransformStrategy.AI_DRIVEN,
                    estimated_complexity=1,
                )
            ],
        )
        system, _ = pb.build_transform_prompt(f, plan)
        assert "my_custom::Old" in system
        assert "my_custom::New" in system

    def test_custom_python_mapping_appears_in_python_system_prompt(self) -> None:
        custom = CustomRules(python_mappings={"my_old.func": "my_new.func"})
        pb = PromptBuilder(custom_rules=custom)
        f = _make_source_file("nodes/node.py", FileType.PYTHON)
        from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy

        plan = MigrationPlan(
            package_name="test_pkg",
            actions=[
                TransformAction(
                    source_path="nodes/node.py",
                    target_path="nodes/node.py",
                    strategy=TransformStrategy.AI_DRIVEN,
                    estimated_complexity=1,
                )
            ],
        )
        system, _ = pb.build_transform_prompt(f, plan)
        assert "my_old.func" in system
        assert "my_new.func" in system

    def test_no_custom_rules_uses_builtins(self) -> None:
        pb = PromptBuilder()
        f = _make_source_file("src/node.cpp", FileType.CPP)
        from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy

        plan = MigrationPlan(
            package_name="test_pkg",
            actions=[
                TransformAction(
                    source_path="src/node.cpp",
                    target_path="src/node.cpp",
                    strategy=TransformStrategy.AI_DRIVEN,
                    estimated_complexity=1,
                )
            ],
        )
        system, _ = pb.build_transform_prompt(f, plan)
        assert "rclcpp" in system

    def test_custom_rules_none_does_not_break_analyze_prompt(self) -> None:
        from pathlib import Path

        from rosforge.models.ir import PackageIR, PackageMetadata

        pb = PromptBuilder(custom_rules=None)
        ir = PackageIR(
            source_path=Path("/tmp/pkg"),
            metadata=PackageMetadata(name="pkg", version="1.0.0"),
            total_files=1,
            total_lines=10,
        )
        system, user = pb.build_analyze_prompt(ir)
        assert isinstance(system, str)
        assert isinstance(user, str)
