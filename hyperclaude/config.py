"""Configuration management for HyperClaude."""

import os
from pathlib import Path
from typing import Any

import yaml

# Default configuration
DEFAULT_CONFIG = {
    "default_workers": 6,
    "default_model": "claude-sonnet-4-20250514",
    "log_retention_days": 7,
    "poll_interval_seconds": 5,
    "tmux_session": "swarm",
    "tmux_window": "main",
}


def get_hyperclaude_dir() -> Path:
    """Get the HyperClaude configuration directory."""
    return Path.home() / ".hyperclaude"


def ensure_directories() -> dict[str, Path]:
    """Create all required HyperClaude directories. Returns dict of paths."""
    base = get_hyperclaude_dir()

    dirs = {
        "base": base,
        "results": base / "results",
        "locks": base / "locks",
        "logs": base / "logs",
        "templates": base / "templates",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_hyperclaude_dir() / "config.yaml"


def load_config() -> dict[str, Any]:
    """Load configuration from file, creating defaults if needed."""
    config_path = get_config_path()

    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        # Merge with defaults
        return {**DEFAULT_CONFIG, **user_config}

    return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    ensure_directories()
    config_path = get_config_path()

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def init_hyperclaude() -> dict[str, Path]:
    """Initialize HyperClaude directories and config. Returns directory paths."""
    dirs = ensure_directories()

    # Create default config if it doesn't exist
    config_path = get_config_path()
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)

    return dirs


def get_result_file(worker_id: int) -> Path:
    """Get the result file path for a worker."""
    return get_hyperclaude_dir() / "results" / f"worker-{worker_id}.txt"


def get_lock_file(worker_id: int) -> Path:
    """Get the lock file path for a worker."""
    return get_hyperclaude_dir() / "locks" / f"worker-{worker_id}.lock"


def get_session_log_dir() -> Path:
    """Get or create a log directory for the current session."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = get_hyperclaude_dir() / "logs" / f"session-{timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir
