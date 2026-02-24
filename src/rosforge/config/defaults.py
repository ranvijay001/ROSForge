"""Default configuration values for ROSForge."""

DEFAULT_CONFIG: dict = {
    "engine": {
        "name": "claude",
        "mode": "cli",
        "timeout_seconds": 300,
        "api_key": "",
        "model": "",
    },
    "migration": {
        "target_ros2_distro": "humble",
        "backup_original": True,
        "init_git": True,
        "output_dir": "",
    },
    "validation": {
        "auto_build": True,
        "rosdep_install": True,
        "max_fix_attempts": 0,
    },
    "telemetry": {
        "enabled": None,
        "local_log": True,
    },
    "verbose": False,
}
