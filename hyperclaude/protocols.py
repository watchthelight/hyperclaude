"""Protocol and state management for hyperclaude swarm."""

import fcntl
import json
import os
import shutil
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from .config import (
    get_hyperclaude_dir,
    get_protocols_dir,
    get_triggers_dir,
    get_worker_state_dir,
    ensure_directories,
    load_config,
    get_session_state_dir,
    get_session_triggers_dir,
    get_session_worker_state_dir,
    get_session_locks_dir,
    get_active_session,
    get_session_info,
    ensure_session_directories,
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
# Active Protocol and Phase (session-aware)
# =============================================================================

def get_state_dir(session: Optional[str] = None) -> Path:
    """Get the state directory for a session."""
    return get_session_state_dir(session)


def set_active_protocol(name: str, session: Optional[str] = None) -> bool:
    """Set the active protocol. Returns False if protocol doesn't exist."""
    if not get_protocol_path(name).exists():
        return False

    session = session or get_active_session() or "swarm"
    ensure_session_directories(session)
    state_file = get_state_dir(session) / "protocol"
    state_file.write_text(name)
    return True


def get_active_protocol(session: Optional[str] = None) -> Optional[str]:
    """Get the currently active protocol name."""
    state_file = get_state_dir(session) / "protocol"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


def set_phase(phase: str, session: Optional[str] = None) -> None:
    """Set the current phase."""
    session = session or get_active_session() or "swarm"
    ensure_session_directories(session)
    state_file = get_state_dir(session) / "phase"
    state_file.write_text(phase)


def get_phase(session: Optional[str] = None) -> Optional[str]:
    """Get the current phase."""
    state_file = get_state_dir(session) / "phase"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


# =============================================================================
# Worker State (JSON-based, session-aware)
# =============================================================================

def get_worker_state_path(worker_id: int, session: Optional[str] = None) -> Path:
    """Get the path to a worker's JSON state file."""
    return get_session_worker_state_dir(session) / f"{worker_id}.json"


def get_worker_state(worker_id: int, session: Optional[str] = None) -> dict[str, Any]:
    """Get the state of a worker as a dict."""
    path = get_worker_state_path(worker_id, session)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {"status": "ready"}


def set_worker_state(worker_id: int, session: Optional[str] = None, reset: bool = False, **kwargs) -> None:
    """Set worker state.

    Args:
        worker_id: Worker ID
        session: Session name
        reset: If True, start fresh (for new tasks). If False, merge with existing.
        **kwargs: State fields to set
    """
    session = session or get_active_session() or "swarm"
    ensure_session_directories(session)

    if reset:
        # Start fresh for new task assignment
        new_state = {"status": "ready"}
    else:
        # Merge with existing state to preserve fields
        new_state = get_worker_state(worker_id, session)

    new_state.update(kwargs)
    path = get_worker_state_path(worker_id, session)
    path.write_text(json.dumps(new_state, indent=2))


def get_all_worker_states(session: Optional[str] = None) -> dict[int, dict[str, Any]]:
    """Get states for all workers."""
    session = session or get_active_session()
    session_info = get_session_info(session) if session else None

    if session_info:
        num_workers = session_info.get("num_workers", 6)
    else:
        config = load_config()
        num_workers = config["default_workers"]

    states = {}
    for i in range(num_workers):
        states[i] = get_worker_state(i, session)
    return states


def clear_worker_states(session: Optional[str] = None) -> None:
    """Clear all worker state files."""
    state_dir = get_session_worker_state_dir(session)
    if state_dir.exists():
        for f in state_dir.glob("*.json"):
            try:
                f.unlink(missing_ok=True)
            except (IOError, OSError):
                # File may have been deleted or locked by another process
                pass


# =============================================================================
# Triggers (session-aware)
# =============================================================================

def create_trigger(name: str, session: Optional[str] = None) -> None:
    """Create a trigger file."""
    session = session or get_active_session() or "swarm"
    ensure_session_directories(session)
    trigger_file = get_session_triggers_dir(session) / name
    trigger_file.touch()


def trigger_exists(name: str, session: Optional[str] = None) -> bool:
    """Check if a trigger file exists."""
    trigger_file = get_session_triggers_dir(session) / name
    return trigger_file.exists()


def clear_trigger(name: str, session: Optional[str] = None) -> None:
    """Remove a trigger file."""
    trigger_file = get_session_triggers_dir(session) / name
    try:
        trigger_file.unlink(missing_ok=True)
    except (IOError, OSError):
        # File may have been deleted by another process
        pass


def await_trigger(name: str, timeout: int = 300, session: Optional[str] = None) -> bool:
    """Wait for a trigger file to appear. Returns True if found, False on timeout."""
    trigger_file = get_session_triggers_dir(session) / name
    start = time.time()

    while time.time() - start < timeout:
        if trigger_file.exists():
            return True
        time.sleep(0.5)

    return False


def clear_all_triggers(session: Optional[str] = None) -> None:
    """Remove all trigger files."""
    triggers_dir = get_session_triggers_dir(session)
    if triggers_dir.exists():
        for f in triggers_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink(missing_ok=True)
                except (IOError, OSError):
                    # File may have been deleted by another process
                    pass


def check_all_workers_done(session: Optional[str] = None) -> bool:
    """Check if all workers are done and create all-done trigger if so."""
    session = session or get_active_session()
    session_info = get_session_info(session) if session else None

    if session_info:
        num_workers = session_info.get("num_workers", 6)
    else:
        config = load_config()
        num_workers = config["default_workers"]

    all_done = True
    for i in range(num_workers):
        if not trigger_exists(f"worker-{i}-done", session):
            all_done = False
            break

    if all_done:
        create_trigger("all-done", session)

    return all_done


# =============================================================================
# Session-Level Locking
# =============================================================================


@contextmanager
def session_lock(session: Optional[str] = None):
    """Context manager for session-level exclusive operations.

    Use this to protect critical sections that modify session state.

    Example:
        with session_lock(session):
            # Critical section - only one process at a time
            modify_session_state()
    """
    session = session or get_active_session() or "swarm"
    ensure_session_directories(session)

    from .config import get_session_dir
    lock_file_path = get_session_dir(session) / ".session.lock"

    lock_file = open(lock_file_path, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


# =============================================================================
# Atomic File Locking
# =============================================================================

def acquire_file_locks(
    worker_id: int,
    files: list[str],
    session: Optional[str] = None
) -> tuple[bool, list[tuple[str, str]]]:
    """Atomically acquire file locks.

    Uses a master lock file with fcntl to ensure atomic check-and-lock.

    Args:
        worker_id: Worker ID requesting locks
        files: List of file paths to lock
        session: Session name

    Returns:
        (success, conflicts) where conflicts is list of (owner, file) tuples
    """
    session = session or get_active_session() or "swarm"
    locks_dir = get_session_locks_dir(session)
    locks_dir.mkdir(parents=True, exist_ok=True)

    master_lock_path = locks_dir / ".master.lock"

    # Open/create master lock file
    with open(master_lock_path, 'w') as master_lock:
        # Acquire exclusive lock on master file
        fcntl.flock(master_lock, fcntl.LOCK_EX)
        try:
            # Check for conflicts while holding master lock
            conflicts = []
            for lock_file in locks_dir.glob("worker-*.lock"):
                if lock_file.stem == f"worker-{worker_id}":
                    continue
                try:
                    locked_files = set(lock_file.read_text().strip().split("\n"))
                    for f in files:
                        if f in locked_files:
                            conflicts.append((lock_file.stem, f))
                except (IOError, OSError):
                    # Lock file may have been deleted concurrently
                    continue

            if conflicts:
                return False, conflicts

            # Write our lock file while still holding master lock
            my_lock = locks_dir / f"worker-{worker_id}.lock"
            my_lock.write_text("\n".join(files))
            return True, []

        finally:
            # Release master lock
            fcntl.flock(master_lock, fcntl.LOCK_UN)


def release_file_locks(worker_id: int, session: Optional[str] = None) -> bool:
    """Release all file locks held by a worker.

    Returns True if locks were released, False if no locks held.
    """
    session = session or get_active_session() or "swarm"
    locks_dir = get_session_locks_dir(session)
    lock_file = locks_dir / f"worker-{worker_id}.lock"

    if lock_file.exists():
        try:
            lock_file.unlink()
            return True
        except (IOError, OSError):
            return False
    return False


def get_all_locks(session: Optional[str] = None) -> dict[str, list[str]]:
    """Get all active file locks.

    Returns dict mapping worker name to list of locked files.
    """
    session = session or get_active_session() or "swarm"
    locks_dir = get_session_locks_dir(session)

    locks = {}
    if locks_dir.exists():
        for lock_file in locks_dir.glob("worker-*.lock"):
            try:
                files = lock_file.read_text().strip().split("\n")
                locks[lock_file.stem] = files
            except (IOError, OSError):
                continue
    return locks


# =============================================================================
# Convenience Functions
# =============================================================================

def reset_swarm_state(session: Optional[str] = None) -> None:
    """Reset all swarm state (workers, triggers, protocol, phase)."""
    clear_worker_states(session)
    clear_all_triggers(session)

    # Clear protocol and phase
    state_dir = get_state_dir(session)
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
