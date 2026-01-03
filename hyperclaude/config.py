"""Configuration management for hyperclaude."""

import json
import os
import re
from pathlib import Path
from typing import Any

import yaml


# =============================================================================
# Constants
# =============================================================================

MAX_WORKERS = 50
MAX_MESSAGE_LENGTH = 100_000  # 100KB
VALID_SESSION_NAME = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


# =============================================================================
# Validation Functions
# =============================================================================

def validate_session_name(name: str) -> str:
    """Validate session name. Raises ValueError if invalid."""
    if not VALID_SESSION_NAME.match(name):
        raise ValueError(
            f"Invalid session name '{name}'. "
            "Use only letters, numbers, hyphens, underscores (max 64 chars)."
        )
    return name


def validate_worker_count(count: int) -> int:
    """Validate worker count. Raises ValueError if invalid."""
    if count < 1:
        raise ValueError("Worker count must be at least 1")
    if count > MAX_WORKERS:
        raise ValueError(f"Maximum {MAX_WORKERS} workers supported")
    return count


def validate_message_length(message: str) -> str:
    """Validate message length. Raises ValueError if too long."""
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message too long ({len(message)} bytes, max {MAX_MESSAGE_LENGTH})"
        )
    return message


def validate_lock_paths(files: tuple[str, ...] | list[str]) -> list[str]:
    """Validate file paths for locking. Raises ValueError if invalid."""
    validated = []
    for f in files:
        if '\n' in f or '\0' in f:
            raise ValueError(f"Invalid characters in path: {f}")
        if '..' in f.split('/'):
            raise ValueError(f"Path traversal not allowed: {f}")
        validated.append(f)
    return validated


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
        "sessions": base / "sessions",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


# =============================================================================
# Multi-Session Management
# =============================================================================

def get_sessions_dir() -> Path:
    """Get the sessions directory."""
    return get_hyperclaude_dir() / "sessions"


def get_session_dir(name: str) -> Path:
    """Get the directory for a specific session."""
    return get_sessions_dir() / name


def ensure_session_directories(name: str) -> dict[str, Path]:
    """Create all directories for a session. Returns dict of paths."""
    session_dir = get_session_dir(name)

    dirs = {
        "base": session_dir,
        "state": session_dir / "state",
        "state_workers": session_dir / "state" / "workers",
        "triggers": session_dir / "triggers",
        "results": session_dir / "results",
        "locks": session_dir / "locks",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def register_session(name: str, workspace: Path, num_workers: int) -> None:
    """Register a new session with its metadata."""
    ensure_session_directories(name)
    session_dir = get_session_dir(name)

    metadata = {
        "name": name,
        "workspace": str(workspace),
        "num_workers": num_workers,
        "tmux_session": name,  # tmux session name = hyperclaude session name
        "tmux_window": "main",
    }

    (session_dir / "session.json").write_text(json.dumps(metadata, indent=2))

    # Set as active session
    set_active_session(name)


def unregister_session(name: str) -> None:
    """Remove a session registration."""
    import shutil
    session_dir = get_session_dir(name)
    if session_dir.exists():
        shutil.rmtree(session_dir)

    # If this was the active session, clear it
    active = get_active_session()
    if active == name:
        active_file = get_hyperclaude_dir() / "active_session"
        if active_file.exists():
            active_file.unlink()


def list_sessions() -> list[dict[str, Any]]:
    """List all registered sessions with their metadata."""
    sessions_dir = get_sessions_dir()
    if not sessions_dir.exists():
        return []

    sessions = []
    for session_dir in sessions_dir.iterdir():
        if session_dir.is_dir():
            metadata_file = session_dir / "session.json"
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                    sessions.append(metadata)
                except json.JSONDecodeError:
                    pass
    return sessions


def get_session_info(name: str) -> dict[str, Any] | None:
    """Get metadata for a specific session."""
    metadata_file = get_session_dir(name) / "session.json"
    if metadata_file.exists():
        try:
            return json.loads(metadata_file.read_text())
        except json.JSONDecodeError:
            pass
    return None


def get_active_session() -> str | None:
    """Get the currently active session name."""
    active_file = get_hyperclaude_dir() / "active_session"
    if active_file.exists():
        name = active_file.read_text().strip()
        # Verify session exists
        if get_session_info(name):
            return name
    return None


def set_active_session(name: str) -> None:
    """Set the active session."""
    ensure_directories()
    active_file = get_hyperclaude_dir() / "active_session"
    active_file.write_text(name)


def get_default_session_name() -> str:
    """Get or generate a default session name."""
    # If there's an active session, use it
    active = get_active_session()
    if active:
        return active
    # Default to "swarm" for backwards compatibility
    return "swarm"


# Session-aware path helpers
def get_session_state_dir(session: str | None = None) -> Path:
    """Get state directory for a session."""
    session = session or get_active_session() or "swarm"
    return get_session_dir(session) / "state"


def get_session_triggers_dir(session: str | None = None) -> Path:
    """Get triggers directory for a session."""
    session = session or get_active_session() or "swarm"
    return get_session_dir(session) / "triggers"


def get_session_results_dir(session: str | None = None) -> Path:
    """Get results directory for a session."""
    session = session or get_active_session() or "swarm"
    return get_session_dir(session) / "results"


def get_session_locks_dir(session: str | None = None) -> Path:
    """Get locks directory for a session."""
    session = session or get_active_session() or "swarm"
    return get_session_dir(session) / "locks"


def get_session_worker_state_dir(session: str | None = None) -> Path:
    """Get worker state directory for a session."""
    session = session or get_active_session() or "swarm"
    return get_session_dir(session) / "state" / "workers"


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


# =============================================================================
# Claude Code Settings Configuration
# =============================================================================

def get_claude_settings_path() -> Path:
    """Get the path to Claude Code's user settings file."""
    return Path.home() / ".claude" / "settings.json"


def configure_claude_permissions() -> bool:
    """
    Configure Claude Code settings to pre-authorize hyperclaude operations.

    Adds the following permissions to ~/.claude/settings.json:
    - Read(~/.hyperclaude/**) - Read hyperclaude config and protocol files
    - Bash(hyperclaude:*) - Run hyperclaude CLI commands

    Returns True if settings were updated, False if already configured.
    """
    settings_path = get_claude_settings_path()

    # Permissions we need for hyperclaude
    required_permissions = [
        "Read(~/.hyperclaude/**)",
        "Bash(hyperclaude:*)",
    ]

    # Load existing settings or create new
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    # Ensure permissions structure exists
    if "permissions" not in settings:
        settings["permissions"] = {}
    if "allow" not in settings["permissions"]:
        settings["permissions"]["allow"] = []

    # Check which permissions are missing
    current_allow = settings["permissions"]["allow"]
    missing = [p for p in required_permissions if p not in current_allow]

    if not missing:
        # Already configured
        return False

    # Add missing permissions
    settings["permissions"]["allow"].extend(missing)

    # Ensure directory exists
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Write updated settings
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")

    return True


def check_claude_permissions() -> dict[str, bool]:
    """
    Check if Claude Code has the required permissions configured.

    Returns a dict mapping permission to whether it's configured.
    """
    settings_path = get_claude_settings_path()

    required_permissions = [
        "Read(~/.hyperclaude/**)",
        "Bash(hyperclaude:*)",
    ]

    if not settings_path.exists():
        return {p: False for p in required_permissions}

    try:
        settings = json.loads(settings_path.read_text())
        current_allow = settings.get("permissions", {}).get("allow", [])
        return {p: p in current_allow for p in required_permissions}
    except json.JSONDecodeError:
        return {p: False for p in required_permissions}
