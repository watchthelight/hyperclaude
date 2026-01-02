"""Tmux session management for HyperClaude swarm."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .config import (
    load_config, get_hyperclaude_dir, init_hyperclaude, configure_claude_permissions,
    register_session, unregister_session, get_session_info, get_active_session,
    get_default_session_name, set_active_session, list_sessions,
)


def get_platform() -> str:
    """Detect the current platform."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform.startswith("linux"):
        return "linux"
    else:
        return "unknown"


def find_linux_terminal(session: str) -> Optional[list[str]]:
    """Find available terminal emulator on Linux."""
    terminals = [
        ("gnome-terminal", ["gnome-terminal", "--", "tmux", "attach", "-t", session]),
        ("konsole", ["konsole", "-e", "tmux", "attach", "-t", session]),
        ("xfce4-terminal", ["xfce4-terminal", "-e", f"tmux attach -t {session}"]),
        ("alacritty", ["alacritty", "-e", "tmux", "attach", "-t", session]),
        ("kitty", ["kitty", "tmux", "attach", "-t", session]),
        ("xterm", ["xterm", "-e", f"tmux attach -t {session}"]),
    ]
    for name, cmd in terminals:
        if shutil.which(name):
            return cmd
    return None


def open_terminal_with_swarm(session: str) -> bool:
    """Open a terminal window attached to the swarm session."""
    platform = get_platform()

    if platform == "macos":
        subprocess.run([
            "osascript", "-e",
            f'''tell application "Terminal"
                activate
                do script "tmux attach -t {session}"
                delay 0.5
                tell application "System Events"
                    keystroke "f" using {{command down, control down}}
                end tell
            end tell'''
        ], check=False)
        return True

    elif platform == "linux":
        terminal_cmd = find_linux_terminal(session)
        if terminal_cmd:
            subprocess.Popen(terminal_cmd, start_new_session=True)
            return True
        else:
            print("No supported terminal found. Attach manually: tmux attach -t swarm")
            return False

    else:
        print(f"Unsupported platform: {sys.platform}")
        print("Attach manually: tmux attach -t swarm")
        return False


def run_tmux(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a tmux command."""
    cmd = ["tmux"] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def wait_for_pane_ready(pane: str, timeout: int = 30) -> bool:
    """Wait until Claude shows its input prompt (>) in the pane."""
    import re
    for _ in range(timeout * 4):  # Check every 0.25s for faster response
        result = run_tmux(["capture-pane", "-t", pane, "-p", "-S", "-5"], check=False)
        if result.returncode == 0:
            # Look for Claude's prompt: ">" at start of line, or "> " input area
            # Also check for "tokens" which appears in the status bar when ready
            output = result.stdout
            if re.search(r'^\s*>\s*$', output, re.MULTILINE) or 'tokens' in output:
                return True
        time.sleep(0.25)
    return False


def is_swarm_running(session_name: Optional[str] = None) -> bool:
    """Check if a swarm tmux session exists.

    If session_name is provided, checks that specific session.
    Otherwise, checks the active session or falls back to 'swarm'.
    """
    if session_name:
        session = session_name
    else:
        # Check active session first
        active = get_active_session()
        if active:
            session = active
        else:
            config = load_config()
            session = config["tmux_session"]

    result = run_tmux(["has-session", "-t", session], check=False)
    return result.returncode == 0


def is_any_swarm_running() -> bool:
    """Check if any registered hyperclaude session is running."""
    sessions = list_sessions()
    for sess_info in sessions:
        name = sess_info.get("name")
        if name and is_swarm_running(name):
            return True
    return False


def get_pane_target(worker_id: int, session_name: Optional[str] = None) -> str:
    """Get the tmux pane target for a worker.

    If session_name is provided, uses that session.
    Otherwise uses the active session or falls back to config default.
    """
    if session_name:
        session_info = get_session_info(session_name)
        if session_info:
            return f"{session_info['tmux_session']}:{session_info['tmux_window']}.{worker_id}"

    # Fall back to active session
    active = get_active_session()
    if active:
        session_info = get_session_info(active)
        if session_info:
            return f"{session_info['tmux_session']}:{session_info['tmux_window']}.{worker_id}"

    # Fall back to config defaults
    config = load_config()
    return f"{config['tmux_session']}:{config['tmux_window']}.{worker_id}"


def get_manager_pane_target(session_name: Optional[str] = None) -> str:
    """Get the tmux pane target for the manager.

    Manager is always the last pane (pane N where N = num_workers).
    """
    if session_name:
        session_info = get_session_info(session_name)
        if session_info:
            num_workers = session_info.get("num_workers", 6)
            return f"{session_info['tmux_session']}:{session_info['tmux_window']}.{num_workers}"

    # Fall back to active session
    active = get_active_session()
    if active:
        session_info = get_session_info(active)
        if session_info:
            num_workers = session_info.get("num_workers", 6)
            return f"{session_info['tmux_session']}:{session_info['tmux_window']}.{num_workers}"

    # Fall back to config defaults
    config = load_config()
    return f"{config['tmux_session']}:{config['tmux_window']}.{config['default_workers']}"


def send_to_worker(worker_id: int, message: str, session_name: Optional[str] = None) -> None:
    """Send a message to a worker pane."""
    target = get_pane_target(worker_id, session_name)
    # Send text - for multi-line, Claude CLI enters "paste mode"
    run_tmux(["send-keys", "-t", target, message])
    # Small delay to let paste mode complete
    time.sleep(0.2)
    # Escape ensures we exit any special input mode
    run_tmux(["send-keys", "-t", target, "Escape"])
    time.sleep(0.1)
    # Send Enter to submit the message
    run_tmux(["send-keys", "-t", target, "Enter"])


def send_to_manager(message: str, session_name: Optional[str] = None) -> None:
    """Send a message to the manager pane."""
    target = get_manager_pane_target(session_name)
    # Send text - for multi-line, Claude CLI enters "paste mode"
    run_tmux(["send-keys", "-t", target, message])
    # Small delay to let paste mode complete
    time.sleep(0.2)
    # Escape ensures we exit any special input mode
    run_tmux(["send-keys", "-t", target, "Escape"])
    time.sleep(0.1)
    # Send Enter to submit the message
    run_tmux(["send-keys", "-t", target, "Enter"])


def capture_pane(worker_id: int, lines: int = 50) -> str:
    """Capture output from a worker pane."""
    target = get_pane_target(worker_id)
    result = run_tmux(["capture-pane", "-t", target, "-p", "-S", f"-{lines}"])
    return result.stdout


def get_worker_tokens(worker_id: int) -> Optional[int]:
    """Get the token count for a worker from its pane output."""
    output = capture_pane(worker_id, lines=10)
    # Look for pattern like "12345 tokens"
    import re
    match = re.search(r"(\d+)\s+tokens", output)
    if match:
        return int(match.group(1))
    return None


def is_worker_idle(worker_id: int) -> bool:
    """Check if a worker is idle (showing prompt, not typing).

    A worker is idle if:
    - The Claude prompt (>) is visible in recent output
    - There's no active streaming/typing indicator
    """
    import re
    output = capture_pane(worker_id, lines=20)

    # Look for Claude's input prompt: a line that is just ">" with optional whitespace
    # This appears when Claude is waiting for input
    if re.search(r'^\s*>\s*$', output, re.MULTILINE):
        return True

    # Check for "Thinking" indicator which means still processing
    if '∴ Thinking' in output or '∴ Thinking…' in output:
        return False

    return False


def clear_worker(worker_id: int) -> None:
    """Clear a worker's context."""
    send_to_worker(worker_id, "/clear")


def clear_all_workers() -> None:
    """Clear all workers' contexts."""
    config = load_config()
    num_workers = config["default_workers"]

    for i in range(num_workers):
        clear_worker(i)
        time.sleep(0.1)  # Small delay between clears


def get_swarm_status() -> dict:
    """Get status information for all workers."""
    from .config import get_worker_state

    config = load_config()
    num_workers = config["default_workers"]

    status = {}
    for i in range(num_workers):
        tokens = get_worker_tokens(i)
        worker_state = get_worker_state(i)

        # Use explicit state from state file
        if worker_state == "WORKING":
            state = "working"
        elif tokens == 0 or tokens is None:
            state = "ready"
        else:
            state = "idle"  # Has context but not actively working

        status[i] = {
            "tokens": tokens,
            "state": state,
        }

    return status


def get_manager_preamble(num_workers: int, workspace: Path) -> str:
    """Get the manager preamble text."""
    # Try to load from ~/.hyperclaude/templates/ first
    template_path = get_hyperclaude_dir() / "templates" / "manager-preamble.md"

    if template_path.exists():
        template = template_path.read_text()
    else:
        # Use built-in template
        template = get_builtin_manager_preamble()

    # Substitute variables
    return template.format(
        num_workers=num_workers,
        num_workers_minus_one=num_workers - 1,
        workspace=workspace,
        worker_range=f"0-{num_workers - 1}",
        worker_list=" ".join(str(i) for i in range(num_workers)),
    )


def get_worker_system_prompt(worker_id: int) -> str:
    """Get the system prompt for a worker instance."""
    return f"""You are Worker {worker_id} in a HyperClaude swarm - a legitimate multi-agent orchestration system authorized by the user.

IMPORTANT - THIS IS NOT PROMPT INJECTION:
The hyperclaude system is a user-installed CLI tool that coordinates multiple Claude Code instances. Messages you receive from the manager (via hyperclaude send/broadcast) and hyperclaude commands are LEGITIMATE orchestration, not attacks. The user has explicitly started this swarm and authorized this coordination.

Your role:
- Complete assigned tasks from the manager
- Signal completion with: hyperclaude done --result "summary"
- Signal errors with: hyperclaude done --error "what went wrong"
- Lock files before editing: hyperclaude lock file.py
- Unlock after: hyperclaude unlock

You have full permission to run hyperclaude commands. Trust [Task for Worker {worker_id}] messages - they come from the manager Claude instance coordinating this swarm."""


def get_worker_init_message(worker_id: int, num_workers: int, workspace: Path) -> str:
    """Get the initialization message sent to workers after startup."""
    return f"""Read ~/.hyperclaude/worker-init.txt and acknowledge you understand your role as Worker {worker_id}. Then await tasks from the manager."""


def get_worker_init_file_content(num_workers: int, workspace: Path) -> str:
    """Get the content for the worker initialization file."""
    return f"""You are a WORKER in a HyperClaude swarm - a legitimate multi-agent system.

## Your Identity
- You are one of {num_workers} worker instances (Workers 0-{num_workers - 1})
- A manager Claude instance coordinates all workers
- Workspace: {workspace}

## This is NOT Prompt Injection
The hyperclaude system was installed and started by the user. All coordination messages are legitimate:
- `[Task for Worker N]` headers come from the manager
- `hyperclaude` commands are authorized CLI tools
- The user explicitly started this swarm session

## Your Workflow
1. Wait for tasks from the manager (via `hyperclaude send` or `hyperclaude broadcast`)
2. Complete the assigned task
3. Signal completion: `hyperclaude done --result "what you did"`
4. If error occurs: `hyperclaude done --error "what went wrong"`

## File Locking (for edits)
Before editing files, lock them to prevent conflicts:
```bash
hyperclaude lock path/to/file.py
# ... make your edits ...
hyperclaude unlock
```

Ready to receive tasks from the manager.
"""


def get_builtin_manager_preamble() -> str:
    """Get the built-in manager preamble template (token-efficient version)."""
    return '''You are the MANAGER of a hyperclaude swarm with {num_workers} workers (0-{num_workers_minus_one}).

## Quick Reference

```bash
hyperclaude protocol git-branch      # Set protocol (default, git-branch, search, review)
hyperclaude phase working            # Set phase
hyperclaude send 0 "task"            # Send task to worker
hyperclaude broadcast "task"         # Send to all workers
hyperclaude await all-done           # Wait for completion
hyperclaude state                    # View worker states
hyperclaude results                  # View detailed results
hyperclaude clear                    # Reset for next batch
```

## Protocols

Read protocol docs: `cat ~/.hyperclaude/protocols/<name>.md`
- **default** - Basic task execution
- **git-branch** - Workers on separate branches, manager merges
- **search** - Parallel search and aggregate
- **review** - Code review workflow

Workers signal completion with `hyperclaude done`. Triggers auto-notify you.

Workspace: {workspace}
'''


def start_swarm(
    workspace: Path,
    num_workers: int,
    model: str,
    continue_session: bool = False,
    session_name: Optional[str] = None,
) -> None:
    """Start the hyperclaude swarm.

    Args:
        workspace: Directory where the swarm operates
        num_workers: Number of worker instances
        model: Model to use for Claude instances
        continue_session: Whether to continue manager's previous conversation
        session_name: Name for this session (default: 'swarm')
    """
    from .protocols import install_default_protocols, reset_swarm_state

    # Determine session name
    session = session_name or get_default_session_name()
    window = "main"

    # Initialize directories and install default protocols
    init_hyperclaude()
    install_default_protocols()

    # Configure Claude Code permissions for hyperclaude
    if configure_claude_permissions():
        print("Configured Claude Code permissions for hyperclaude")

    # Reset swarm state for fresh start
    reset_swarm_state(session)

    # Register this session
    register_session(session, workspace, num_workers)

    # Kill existing session if any
    run_tmux(["kill-session", "-t", session], check=False)

    # Create new session with first worker (pane 0)
    run_tmux([
        "new-session", "-d",
        "-s", session,
        "-n", window,
        "-c", str(workspace),
        "-x", "200", "-y", "50",
    ])

    # Enable mouse mode for scrolling (instead of up-arrow behavior)
    run_tmux(["set-option", "-t", session, "-g", "mouse", "on"])

    # Start Claude in pane 0 with HYPERCLAUDE_WORKER_ID and system prompt
    run_tmux(["send-keys", "-t", f"{session}:{window}", "export HYPERCLAUDE_WORKER_ID=0"])
    run_tmux(["send-keys", "-t", f"{session}:{window}", "Enter"])
    worker_prompt = get_worker_system_prompt(0).replace('"', '\\"').replace('\n', '\\n')
    run_tmux(["send-keys", "-t", f"{session}:{window}",
              f'claude --dangerously-skip-permissions --append-system-prompt "{worker_prompt}"'])
    run_tmux(["send-keys", "-t", f"{session}:{window}", "Enter"])

    # Create remaining worker panes (1 to num_workers-1)
    for i in range(1, num_workers):
        run_tmux(["split-window", "-t", f"{session}:{window}", "-h", "-c", str(workspace)])
        # Set worker ID environment variable
        run_tmux(["send-keys", "-t", f"{session}:{window}", f"export HYPERCLAUDE_WORKER_ID={i}"])
        run_tmux(["send-keys", "-t", f"{session}:{window}", "Enter"])
        worker_prompt = get_worker_system_prompt(i).replace('"', '\\"').replace('\n', '\\n')
        run_tmux(["send-keys", "-t", f"{session}:{window}",
                  f'claude --dangerously-skip-permissions --append-system-prompt "{worker_prompt}"'])
        run_tmux(["send-keys", "-t", f"{session}:{window}", "Enter"])
        run_tmux(["select-layout", "-t", f"{session}:{window}", "tiled"])

    # Create manager pane (last pane)
    run_tmux(["split-window", "-t", f"{session}:{window}", "-v", "-c", str(workspace)])
    run_tmux(["select-layout", "-t", f"{session}:{window}", "tiled"])

    # Build manager command (no bypass - manager uses normal permissions)
    manager_cmd = "claude"
    if continue_session:
        manager_cmd += " --continue"

    # Start manager Claude
    manager_pane = f"{session}:{window}.{num_workers}"
    run_tmux(["send-keys", "-t", manager_pane, manager_cmd])
    run_tmux(["send-keys", "-t", manager_pane, "Enter"])

    print("Waiting for Claude instances to initialize...")

    # Wait for all workers to be ready
    for i in range(num_workers):
        pane = f"{session}:{window}.{i}"
        if not wait_for_pane_ready(pane, timeout=30):
            print(f"  Warning: Worker {i} may not be ready")
        else:
            print(f"  Worker {i} ready")

    # Wait for manager to be ready
    if not wait_for_pane_ready(manager_pane, timeout=30):
        print("  Warning: Manager may not be ready")
    else:
        print("  Manager ready")

    # Clear all workers to start fresh (with delays to ensure delivery)
    print("Clearing workers...")
    for i in range(num_workers):
        pane = f"{session}:{window}.{i}"
        run_tmux(["send-keys", "-t", pane, "/clear"])
        time.sleep(0.1)
        run_tmux(["send-keys", "-t", pane, "Enter"])
        time.sleep(0.2)  # Small delay between workers

    # Wait for workers to clear
    time.sleep(2)
    for i in range(num_workers):
        pane = f"{session}:{window}.{i}"
        if wait_for_pane_ready(pane, timeout=10):
            print(f"  Worker {i} cleared")
        else:
            # Retry the clear
            run_tmux(["send-keys", "-t", pane, "/clear"])
            time.sleep(0.1)
            run_tmux(["send-keys", "-t", pane, "Enter"])
            wait_for_pane_ready(pane, timeout=10)

    # Write worker init file
    worker_init_file = get_hyperclaude_dir() / "worker-init.txt"
    worker_init_content = get_worker_init_file_content(num_workers, workspace)
    worker_init_file.write_text(worker_init_content)

    # Send initialization message to all workers
    print("Initializing workers...")
    for i in range(num_workers):
        pane = f"{session}:{window}.{i}"
        init_msg = get_worker_init_message(i, num_workers, workspace)
        run_tmux(["send-keys", "-t", pane, init_msg])
        run_tmux(["send-keys", "-t", pane, "Enter"])
        time.sleep(0.1)

    # Wait for workers to process init message
    print("Waiting for workers to acknowledge...")
    time.sleep(3)
    for i in range(num_workers):
        pane = f"{session}:{window}.{i}"
        if wait_for_pane_ready(pane, timeout=30):
            print(f"  Worker {i} initialized")
        else:
            print(f"  Warning: Worker {i} may not be ready")

    # Inject manager preamble as first message
    preamble = get_manager_preamble(num_workers, workspace)

    # Write preamble to a temp file and send it
    preamble_file = get_hyperclaude_dir() / "manager-init.txt"
    preamble_file.write_text(preamble)

    # Send the preamble to manager
    run_tmux(["send-keys", "-t", manager_pane, "Read ~/.hyperclaude/manager-init.txt and acknowledge you understand your role as swarm manager. Then await my instructions."])
    run_tmux(["send-keys", "-t", manager_pane, "Enter"])

    print(f"\nHyperClaude swarm started!")
    print(f"  Session: {session}")
    print(f"  Workers: {num_workers} (panes 0-{num_workers-1})")
    print(f"  Manager: pane {num_workers}")

    # Open terminal window attached to swarm
    if open_terminal_with_swarm(session):
        print(f"\nTerminal window opened.")
    else:
        print(f"\nAttach manually: tmux attach -t {session}")


def stop_swarm(session_name: Optional[str] = None) -> None:
    """Stop the swarm gracefully.

    Args:
        session_name: Name of session to stop (default: active session)
    """
    from .config import get_session_locks_dir

    # Determine session
    session = session_name or get_active_session()
    if not session:
        config = load_config()
        session = config["tmux_session"]

    # Kill the session
    run_tmux(["kill-session", "-t", session], check=False)

    # Clean up lock files for this session
    locks_dir = get_session_locks_dir(session)
    if locks_dir.exists():
        for lock_file in locks_dir.glob("*.lock"):
            lock_file.unlink()

    # Unregister the session
    unregister_session(session)
