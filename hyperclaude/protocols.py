"""Protocol and state management for hyperclaude swarm."""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from .config import (
    get_hyperclaude_dir,
    get_protocols_dir,
    get_triggers_dir,
    get_worker_state_dir,
    ensure_directories,
    load_config,
)


# =============================================================================
# Protocol Management
# =============================================================================

def get_builtin_protocols_dir() -> Path:
    """Get the directory containing built-in protocol templates."""
    return Path(__file__).parent / "templates" / "protocols"


def list_protocols() -> list[str]:
    """List all available protocols."""
    protocols_dir = get_protocols_dir()
    if not protocols_dir.exists():
        return []

    protocols = []
    for f in protocols_dir.glob("*.md"):
        protocols.append(f.stem)
    return sorted(protocols)


def get_protocol_path(name: str) -> Path:
    """Get the path to a protocol file."""
    return get_protocols_dir() / f"{name}.md"


def get_protocol(name: str) -> Optional[str]:
    """Read a protocol file. Returns None if not found."""
    path = get_protocol_path(name)
    if path.exists():
        return path.read_text()
    return None


def install_default_protocols() -> None:
    """Copy built-in protocols to user's protocols directory if not present."""
    ensure_directories()
    builtin_dir = get_builtin_protocols_dir()
    user_dir = get_protocols_dir()

    if not builtin_dir.exists():
        return

    for protocol_file in builtin_dir.glob("*.md"):
        dest = user_dir / protocol_file.name
        if not dest.exists():
            shutil.copy(protocol_file, dest)


# =============================================================================
# Active Protocol and Phase
# =============================================================================

def get_state_dir() -> Path:
    """Get the state directory."""
    return get_hyperclaude_dir() / "state"


def set_active_protocol(name: str) -> bool:
    """Set the active protocol. Returns False if protocol doesn't exist."""
    if not get_protocol_path(name).exists():
        return False

    ensure_directories()
    state_file = get_state_dir() / "protocol"
    state_file.write_text(name)
    return True


def get_active_protocol() -> Optional[str]:
    """Get the currently active protocol name."""
    state_file = get_state_dir() / "protocol"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


def set_phase(phase: str) -> None:
    """Set the current phase."""
    ensure_directories()
    state_file = get_state_dir() / "phase"
    state_file.write_text(phase)


def get_phase() -> Optional[str]:
    """Get the current phase."""
    state_file = get_state_dir() / "phase"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


# =============================================================================
# Worker State (JSON-based)
# =============================================================================

def get_worker_state_path(worker_id: int) -> Path:
    """Get the path to a worker's JSON state file."""
    return get_worker_state_dir() / f"{worker_id}.json"


def get_worker_state(worker_id: int) -> dict[str, Any]:
    """Get the state of a worker as a dict."""
    path = get_worker_state_path(worker_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {"status": "ready"}


def set_worker_state(worker_id: int, **kwargs) -> None:
    """Update a worker's state. Merges with existing state."""
    ensure_directories()
    current = get_worker_state(worker_id)
    current.update(kwargs)
    path = get_worker_state_path(worker_id)
    path.write_text(json.dumps(current, indent=2))


def get_all_worker_states() -> dict[int, dict[str, Any]]:
    """Get states for all workers."""
    config = load_config()
    num_workers = config["default_workers"]

    states = {}
    for i in range(num_workers):
        states[i] = get_worker_state(i)
    return states


def clear_worker_states() -> None:
    """Clear all worker state files."""
    state_dir = get_worker_state_dir()
    if state_dir.exists():
        for f in state_dir.glob("*.json"):
            f.unlink()


# =============================================================================
# Triggers
# =============================================================================

def create_trigger(name: str) -> None:
    """Create a trigger file."""
    ensure_directories()
    trigger_file = get_triggers_dir() / name
    trigger_file.touch()


def trigger_exists(name: str) -> bool:
    """Check if a trigger file exists."""
    trigger_file = get_triggers_dir() / name
    return trigger_file.exists()


def clear_trigger(name: str) -> None:
    """Remove a trigger file."""
    trigger_file = get_triggers_dir() / name
    if trigger_file.exists():
        trigger_file.unlink()


def await_trigger(name: str, timeout: int = 300) -> bool:
    """Wait for a trigger file to appear. Returns True if found, False on timeout."""
    trigger_file = get_triggers_dir() / name
    start = time.time()

    while time.time() - start < timeout:
        if trigger_file.exists():
            return True
        time.sleep(0.5)

    return False


def clear_all_triggers() -> None:
    """Remove all trigger files."""
    triggers_dir = get_triggers_dir()
    if triggers_dir.exists():
        for f in triggers_dir.iterdir():
            if f.is_file():
                f.unlink()


def check_all_workers_done() -> bool:
    """Check if all workers are done and create all-done trigger if so."""
    config = load_config()
    num_workers = config["default_workers"]

    all_done = True
    for i in range(num_workers):
        if not trigger_exists(f"worker-{i}-done"):
            all_done = False
            break

    if all_done:
        create_trigger("all-done")

    return all_done


# =============================================================================
# Convenience Functions
# =============================================================================

def reset_swarm_state() -> None:
    """Reset all swarm state (workers, triggers, protocol, phase)."""
    clear_worker_states()
    clear_all_triggers()

    # Clear protocol and phase
    state_dir = get_state_dir()
    for name in ["protocol", "phase"]:
        path = state_dir / name
        if path.exists():
            path.unlink()


def get_worker_id_from_env() -> Optional[int]:
    """Get worker ID from HYPERCLAUDE_WORKER_ID environment variable."""
    worker_id = os.environ.get("HYPERCLAUDE_WORKER_ID")
    if worker_id is not None:
        try:
            return int(worker_id)
        except ValueError:
            pass
    return None
