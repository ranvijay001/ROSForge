"""ROS1 → ROS2 launch file transformation rules.

Provides ``transform_launch_xml()`` which converts a ROS1 ``roslaunch`` XML
file into a valid ROS2 Python launch file string.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# Pre-compiled pattern to detect <group ns="..."> elements
_re_group_ns = re.compile(r"<group\s[^>]*\bns\s*=")


def _attr(el: ET.Element, name: str, default: str = "") -> str:
    """Return an element attribute value or *default* if missing."""
    return el.get(name, default)


def _quote(value: str) -> str:
    """Wrap *value* in double quotes, escaping existing double quotes."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _is_substitution(value: str) -> bool:
    """Return True if *value* contains a ROS1 substitution argument."""
    return "$(arg " in value or "$(find " in value or "$(env " in value


def _convert_substitution(value: str) -> str:
    """Convert ROS1 substitution syntax to ROS2 Python launch equivalents.

    Handles:
    - ``$(arg name)``  → ``LaunchConfiguration('name')``
    - ``$(find pkg)``  → ``FindPackageShare('pkg')``
    - ``$(env VAR)``   → ``EnvironmentVariable('VAR')``
    """
    value = re.sub(
        r"\$\(arg\s+(\w+)\)",
        lambda m: f"LaunchConfiguration('{m.group(1)}')",
        value,
    )
    value = re.sub(
        r"\$\(find\s+([\w_]+)\)",
        lambda m: f"FindPackageShare('{m.group(1)}')",
        value,
    )
    value = re.sub(
        r"\$\(env\s+(\w+)\)",
        lambda m: f"EnvironmentVariable('{m.group(1)}')",
        value,
    )
    return value


def _python_value(value: str) -> str:
    """Return a Python expression for a launch attribute value."""
    if _is_substitution(value):
        converted = _convert_substitution(value)
        return converted
    return _quote(value)


def _node_to_python(el: ET.Element, indent: str = "        ") -> str:
    """Convert a <node> element to a ROS2 Node() action string."""
    pkg = _attr(el, "pkg")
    exec_name = _attr(el, "type") or _attr(el, "exec")
    name = _attr(el, "name") or exec_name
    ns = _attr(el, "ns", "")
    output = _attr(el, "output", "screen")
    args = _attr(el, "args", "")
    respawn = _attr(el, "respawn", "false")

    lines: list[str] = [f"{indent}Node("]
    lines.append(f"{indent}    package={_python_value(pkg)},")
    lines.append(f"{indent}    executable={_python_value(exec_name)},")
    lines.append(f"{indent}    name={_python_value(name)},")
    if ns:
        lines.append(f"{indent}    namespace={_python_value(ns)},")
    lines.append(f"{indent}    output={_python_value(output)},")

    params: list[str] = []
    remaps: list[str] = []

    for param_el in el.findall("param"):
        pname = _attr(param_el, "name")
        pvalue = _attr(param_el, "value")
        if pname and pvalue:
            params.append(f"({_python_value(pname)}, {_python_value(pvalue)})")

    for remap_el in el.findall("remap"):
        from_topic = _attr(remap_el, "from")
        to_topic = _attr(remap_el, "to")
        if from_topic and to_topic:
            remaps.append(f"({_python_value(from_topic)}, {_python_value(to_topic)})")

    if params:
        params_str = ", ".join(params)
        lines.append(f"{indent}    parameters=[{{{params_str}}}],")

    if remaps:
        remaps_str = ", ".join(remaps)
        lines.append(f"{indent}    remappings=[{remaps_str}],")

    if args:
        lines.append(f"{indent}    arguments=[{_python_value(args)}],")

    if respawn.lower() == "true":
        lines.append(f"{indent}    respawn=True,")

    lines.append(f"{indent}),")
    return "\n".join(lines)


def _include_to_python(el: ET.Element, indent: str = "        ") -> str:
    """Convert an <include> element to a ROS2 IncludeLaunchDescription() call."""
    file_attr = _attr(el, "file")
    file_expr = _python_value(file_attr)

    arg_lines: list[str] = []
    for arg_el in el.findall("arg"):
        aname = _attr(arg_el, "name")
        avalue = _attr(arg_el, "value", "")
        if aname and avalue:
            arg_lines.append(f"{indent}        ({_python_value(aname)}, {_python_value(avalue)})")

    lines = [
        f"{indent}IncludeLaunchDescription(",
        f"{indent}    PythonLaunchDescriptionSource({file_expr}),",
    ]
    if arg_lines:
        lines.append(f"{indent}    launch_arguments=[")
        lines.extend(f"{al}," for al in arg_lines)
        lines.append(f"{indent}    ].items(),")
    lines.append(f"{indent}),")
    return "\n".join(lines)


def _arg_to_python(el: ET.Element, indent: str = "        ") -> str:
    """Convert an <arg> element to a ROS2 DeclareLaunchArgument() call."""
    name = _attr(el, "name")
    default = _attr(el, "default", "")
    description = _attr(el, "doc", "")
    value = _attr(el, "value", "")

    if value:
        return f"{indent}# arg '{name}' has constant value={_quote(value)}"

    kwargs: list[str] = [f"name={_quote(name)}"]
    if default:
        kwargs.append(f"default_value={_python_value(default)}")
    if description:
        kwargs.append(f"description={_quote(description)}")

    kwargs_str = ", ".join(kwargs)
    return f"{indent}DeclareLaunchArgument({kwargs_str}),"


def _param_to_python(el: ET.Element, indent: str = "        ") -> str:
    """Convert a top-level <param> element to a SetParameter() action."""
    name = _attr(el, "name")
    value = _attr(el, "value")
    return f"{indent}SetParameter(name={_quote(name)}, value={_python_value(value)}),"


def transform_launch_xml(original: str) -> str:
    """Transform a ROS1 XML launch file to a ROS2 Python launch file.

    Args:
        original: Full text of the ROS1 .launch XML file.

    Returns:
        Python source code for the equivalent ROS2 launch file, including
        all necessary imports and a ``generate_launch_description()`` function.
    """
    try:
        root = ET.fromstring(original.strip())
    except ET.ParseError:
        root = ET.fromstring(f"<launch>{original.strip()}</launch>")

    needs_find_pkg_share = "$(find " in original
    needs_env_var = "$(env " in original
    has_env_element = "<env " in original
    has_group_ns = bool(_re_group_ns.search(original))

    import_lines = [
        "from launch import LaunchDescription",
        "from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription",
        "from launch.actions import GroupAction, SetParameter",
    ]
    if has_env_element:
        import_lines.append("from launch.actions import SetEnvironmentVariable")
    if has_group_ns:
        import_lines.append("from launch_ros.actions import PushRosNamespace")
    import_lines += [
        "from launch.launch_description_sources import PythonLaunchDescriptionSource",
        "from launch.substitutions import LaunchConfiguration",
    ]
    if needs_find_pkg_share:
        import_lines.append("from launch_ros.substitutions import FindPackageShare")
    if needs_env_var:
        import_lines.append("from launch.substitutions import EnvironmentVariable")
    import_lines.append("from launch_ros.actions import Node")

    lines: list[str] = []
    lines.extend(import_lines)
    lines.append("")
    lines.append("")
    lines.append("def generate_launch_description():")
    lines.append("    return LaunchDescription([")

    for child in root:
        tag = child.tag
        if tag == "node":
            lines.append(_node_to_python(child))
        elif tag == "include":
            lines.append(_include_to_python(child))
        elif tag == "arg":
            lines.append(_arg_to_python(child))
        elif tag == "param":
            lines.append(_param_to_python(child))
        elif tag == "env":
            env_name = _attr(child, "name")
            env_value = _attr(child, "value")
            lines.append(
                f"        SetEnvironmentVariable(name={_quote(env_name)}, value={_python_value(env_value)}),"
            )
        elif tag == "group":
            ns = _attr(child, "ns", "")
            group_children: list[str] = []
            for sub in child:
                if sub.tag == "node":
                    group_children.append(_node_to_python(sub, indent="            "))
                elif sub.tag == "include":
                    group_children.append(_include_to_python(sub, indent="            "))
                elif sub.tag == "arg":
                    group_children.append(_arg_to_python(sub, indent="            "))
                elif sub.tag == "env":
                    env_name = _attr(sub, "name")
                    env_value = _attr(sub, "value")
                    group_children.append(
                        f"            SetEnvironmentVariable(name={_quote(env_name)}, value={_python_value(env_value)}),"
                    )
            if ns:
                lines.append("        GroupAction(actions=[")
                lines.append(f"            PushRosNamespace({_python_value(ns)}),")
                lines.extend(group_children)
                lines.append("        ]),")
            else:
                lines.extend(group_children)
        elif tag == "rosparam":
            lines.append("        # rosparam: convert manually to YAML parameter files")
        elif tag == "machine":
            machine_name = _attr(child, "name", "remote_machine")
            machine_addr = _attr(child, "address", "REMOTE_HOST")
            lines.append(
                "        # <machine> tag has no ROS2 equivalent — use SSH launch or a remote launch approach"
            )
            lines.append(
                f"        # Original machine: name={machine_name!r}, address={machine_addr!r}"
            )
        elif tag == "test":
            test_pkg = _attr(child, "pkg", "unknown_pkg")
            test_type = _attr(child, "type", "unknown_node")
            test_name = _attr(child, "test-name", test_type)
            lines.append("        # <test> tag: migrate to launch_testing framework")
            lines.append(
                f"        # Original: pkg={test_pkg!r}, type={test_type!r}, test-name={test_name!r}"
            )

    lines.append("    ])")
    lines.append("")

    return "\n".join(lines)
