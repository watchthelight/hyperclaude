"""Configuration management for HyperClaude."""

import os
from pathlib import Path
from typing import Any

import yaml

# Default configuration
DEFAULT_CONFIG = {
    "default_workers": 6,
    "default_model": "claude-opus-4-20250514",
    "log_retention_days": 7,
    "poll_interval_seconds": 5,
    "tmux_session": "swarm",
    "tmux_window": "main",
}


def get_hyperclaude_dir() -> Path:
    """Get the HyperClaude configuration directory."""
    return Path.home() / ".hyperclaude"


def ensure_directories() -> dict[str, Path]:
    """Create all required hyperclaude directories. Returns dict of paths."""
    base = get_hyperclaude_dir()

    dirs = {
        "base": base,
        "results": base / "results",
        "locks": base / "locks",
        "logs": base / "logs",
        "templates": base / "templates",
        "state": base / "state",
        "state_workers": base / "state" / "workers",
        "protocols": base / "protocols",
        "triggers": base / "triggers",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def get_protocols_dir() -> Path:
    """Get the protocols directory."""
    return get_hyperclaude_dir() / "protocols"


def get_triggers_dir() -> Path:
    """Get the triggers directory."""
    return get_hyperclaude_dir() / "triggers"


def get_worker_state_dir() -> Path:
    """Get the worker state directory (for JSON state files)."""
    return get_hyperclaude_dir() / "state" / "workers"


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


def get_state_file(worker_id: int) -> Path:
    """Get the state file path for a worker."""
    return get_hyperclaude_dir() / "state" / f"worker-{worker_id}.state"


def get_worker_state(worker_id: int) -> str:
    """Get the current state of a worker. Returns 'READY', 'WORKING', or 'UNKNOWN'."""
    state_file = get_state_file(worker_id)
    if state_file.exists():
        return state_file.read_text().strip()
    return "READY"


def set_worker_state(worker_id: int, state: str) -> None:
    """Set the state of a worker ('READY' or 'WORKING')."""
    ensure_directories()
    state_file = get_state_file(worker_id)
    state_file.write_text(state)


def clear_all_worker_states() -> None:
    """Clear all worker state files (set all to READY)."""
    state_dir = get_hyperclaude_dir() / "state"
    if state_dir.exists():
        for state_file in state_dir.glob("*.state"):
            state_file.unlink()
