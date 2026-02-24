# ROSForge

**AI-driven ROS1 to ROS2 migration CLI tool.**

[![CI](https://img.shields.io/github/actions/workflow/status/Rlin1027/ROSForge/ci.yml?branch=main&label=CI)](https://github.com/Rlin1027/ROSForge/actions) [![PyPI](https://img.shields.io/pypi/v/rosforge)](https://pypi.org/project/rosforge/) [![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

## Why ROSForge?

ROS1 reached end-of-life in May 2025. Migrating a production codebase to ROS2 by hand is tedious and error-prone: API namespaces changed, CMakeLists.txt rules are different, launch files moved to Python, and hundreds of `ros::` calls need one-by-one replacement. ROSForge automates this work by combining a static knowledge base of known API mappings with an AI backend that handles the cases rules alone cannot cover. The result is a complete, confidence-scored migration in minutes rather than days.

## Features

- **Full pipeline** — analyze, transform, validate, and report in a single command
- **BYOM (Bring Your Own Model)** — Claude, Gemini, and OpenAI backends; CLI or API mode
- **Auto-fix loop** — runs `colcon build`, feeds errors back to the AI, retries up to N times
- **Interactive mode** — per-file diff review; accept or skip each transformed file
- **Batch workspace migration** — migrate an entire catkin workspace in one pass
- **Custom transformation rules** — override or extend mappings with a YAML file
- **Static knowledge base** — built-in C++/Python API mappings, CMake rules, and launch conversion patterns
- **Cost estimation** — token and USD estimates shown before any API calls are made
- **Confidence scoring** — every output file is rated HIGH / MEDIUM / LOW; low-confidence files are flagged for manual review

## Quick Start

```bash
# Install
pip install rosforge

# Set your preferred AI backend (stored in ~/.config/rosforge/config.toml)
rosforge config set engine.name gemini
rosforge config set engine.mode cli

# Migrate a single ROS1 package
rosforge migrate ./my_ros1_package -o ./my_ros1_package_ros2
```

The migrated package and a `migration_report.md` are written to the output directory.

## Commands

| Command | Description |
|---|---|
| `rosforge migrate <path>` | Migrate a single ROS1 package to ROS2 |
| `rosforge migrate-workspace <path>` | Migrate all packages in a catkin workspace |
| `rosforge analyze <path>` | Analyze a package and report migration complexity without transforming |
| `rosforge config set <key> <value>` | Set a configuration value and persist it |
| `rosforge config get <key>` | Get a single configuration value |
| `rosforge config list` | Print all current configuration values as JSON |
| `rosforge config reset` | Reset configuration to defaults |
| `rosforge config path` | Show the path to the configuration file |
| `rosforge status` | Show the status of an in-progress or completed migration |

## AI Engine Configuration

ROSForge supports three AI backends. Each can run in **cli** mode (calls a locally installed CLI tool, no API key required) or **api** mode (calls the provider's REST API directly, requires an API key).

### Claude

```bash
# CLI mode — requires the Anthropic Claude CLI installed and authenticated
rosforge config set engine.name claude
rosforge config set engine.mode cli

# API mode — requires ANTHROPIC_API_KEY
pip install "rosforge[claude]"
rosforge config set engine.name claude
rosforge config set engine.mode api
export ANTHROPIC_API_KEY=sk-ant-...
```

### Gemini

```bash
# CLI mode — requires the Google Gemini CLI installed and authenticated
rosforge config set engine.name gemini
rosforge config set engine.mode cli

# API mode — requires GOOGLE_API_KEY
pip install "rosforge[gemini]"
rosforge config set engine.name gemini
rosforge config set engine.mode api
export GOOGLE_API_KEY=AIza...
```

### OpenAI

```bash
# API mode — requires OPENAI_API_KEY
pip install "rosforge[openai]"
rosforge config set engine.name openai
rosforge config set engine.mode api
export OPENAI_API_KEY=sk-...
```

Install all backends at once:

```bash
pip install "rosforge[all]"
```

## Advanced Usage

### Interactive review

Review each transformed file before it is written:

```bash
rosforge migrate ./my_package --interactive
```

Press `a` to accept, `s` to skip, `q` to quit and accept all remaining files.

### Auto-fix loop

Build the output with `colcon build` after migration, feed any errors back to the AI, and retry:

```bash
rosforge migrate ./my_package --max-fix-attempts 3
```

### Custom rules

Supply additional or overriding transformation mappings:

```bash
rosforge migrate ./my_package --rules custom_rules.yaml
```

### Skip confirmation

Skip the cost-estimate confirmation prompt (useful in CI):

```bash
rosforge migrate ./my_package --yes
```

### Target ROS2 distribution

The default target is `humble`. To target a different distribution:

```bash
rosforge migrate ./my_package --distro jazzy
```

### Workspace migration

```bash
rosforge migrate-workspace ./catkin_ws -o ./ros2_ws --engine gemini --yes
```

### Analyze without migrating

```bash
# Rich table output in the terminal
rosforge analyze ./my_package

# Machine-readable JSON
rosforge analyze ./my_package --json

# Save JSON report to file
rosforge analyze ./my_package -o analysis.json
```

## Custom Rules

Create a YAML file to add or override transformation mappings:

```yaml
# custom_rules.yaml
version: 1

api_mappings:
  cpp:
    "ros::NodeHandle": "rclcpp::Node"
    "ros::Publisher": "rclcpp::Publisher"
  python:
    "rospy.init_node": "rclpy.init"
    "rospy.Publisher": "rclpy.create_publisher"

package_mappings:
  "roscpp": "rclcpp"
  "rospy": "rclpy"

cmake_mappings:
  "find_package(catkin REQUIRED": "find_package(ament_cmake REQUIRED"
```

Pass the file with `--rules custom_rules.yaml`. Custom mappings take precedence over the built-in knowledge base.

## Development

```bash
git clone https://github.com/Rlin1027/ROSForge.git
cd ROSForge
pip install -e ".[dev,all]"
pytest tests/
```

Lint and type-check:

```bash
ruff check src/
mypy src/
```

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
