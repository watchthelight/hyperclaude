"""Tmux session management for HyperClaude swarm."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from .config import load_config, get_hyperclaude_dir, init_hyperclaude


def get_platform() -> str:
    """Detect the current platform."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform.startswith("linux"):
        return "linux"
    else:
        return "unknown"


def find_linux_terminal() -> Optional[list[str]]:
    """Find available terminal emulator on Linux."""
    terminals = [
        ("gnome-terminal", ["gnome-terminal", "--", "tmux", "attach", "-t", "swarm"]),
        ("konsole", ["konsole", "-e", "tmux", "attach", "-t", "swarm"]),
        ("xfce4-terminal", ["xfce4-terminal", "-e", "tmux attach -t swarm"]),
        ("alacritty", ["alacritty", "-e", "tmux", "attach", "-t", "swarm"]),
        ("kitty", ["kitty", "tmux", "attach", "-t", "swarm"]),
        ("xterm", ["xterm", "-e", "tmux", "attach", "-t", "swarm"]),
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
        terminal_cmd = find_linux_terminal()
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


def is_swarm_running() -> bool:
    """Check if a swarm tmux session exists."""
    config = load_config()
    session = config["tmux_session"]

    result = run_tmux(["has-session", "-t", session], check=False)
    return result.returncode == 0


def get_pane_target(worker_id: int) -> str:
    """Get the tmux pane target for a worker."""
    config = load_config()
    return f"{config['tmux_session']}:{config['tmux_window']}.{worker_id}"


def send_to_worker(worker_id: int, message: str) -> None:
    """Send a message to a worker pane."""
    target = get_pane_target(worker_id)
    # Send text and then Enter separately (critical for Claude CLI)
    run_tmux(["send-keys", "-t", target, message])
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
    config = load_config()
    num_workers = config["default_workers"]

    status = {}
    for i in range(num_workers):
        tokens = get_worker_tokens(i)
        if tokens == 0:
            state = "ready"
        elif tokens is None:
            state = "unknown"
        else:
            state = "active"

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


def get_builtin_manager_preamble() -> str:
    """Get the built-in manager preamble template."""
    return '''You are the MANAGER in a HyperClaude swarm. You coordinate {num_workers} worker Claude instances (Workers 0-{num_workers_minus_one}).

## CLI Commands

**Send task to one worker:**
```bash
hyperclaude send 0 "Search for TODO comments in src/"
```

**Send task to ALL workers:**
```bash
hyperclaude broadcast "Find security vulnerabilities"
```

**Wait for all workers to finish:**
```bash
hyperclaude wait
```

**Check worker status:**
```bash
hyperclaude status
```

**View results:**
```bash
hyperclaude results
```

**Clear all workers:**
```bash
hyperclaude clear
```

**Check file locks:**
```bash
hyperclaude locks
```

## How It Works

1. Use `hyperclaude send N "task"` to assign work to worker N
2. The worker receives the task with instructions to use `hyperclaude report` when done
3. Use `hyperclaude wait` to block until all workers finish
4. Use `hyperclaude results` to see all outputs

Workers automatically get instructions to:
- Run `hyperclaude report "result"` when done
- Run `hyperclaude lock file.py` before editing files
- Run `hyperclaude unlock` when done editing

## Best Practices

1. **Divide by file** - assign different workers to different files/directories
2. **Use broadcast** for parallel searches across the codebase
3. **Use send** for specific tasks that need one worker
4. **Check locks** if workers report conflicts

Current workspace: {workspace}
'''


def start_swarm(
    workspace: Path,
    num_workers: int,
    model: str,
    continue_session: bool = False,
) -> None:
    """Start the HyperClaude swarm."""
    config = load_config()
    session = config["tmux_session"]
    window = config["tmux_window"]

    # Initialize directories
    init_hyperclaude()

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

    # Start Claude in pane 0 (Enter must be separate!)
    run_tmux(["send-keys", "-t", f"{session}:{window}", "claude --dangerously-skip-permissions"])
    run_tmux(["send-keys", "-t", f"{session}:{window}", "Enter"])

    # Create remaining worker panes (1 to num_workers-1)
    for i in range(1, num_workers):
        run_tmux(["split-window", "-t", f"{session}:{window}", "-h", "-c", str(workspace)])
        run_tmux(["send-keys", "-t", f"{session}:{window}", "claude --dangerously-skip-permissions"])
        run_tmux(["send-keys", "-t", f"{session}:{window}", "Enter"])
        run_tmux(["select-layout", "-t", f"{session}:{window}", "tiled"])

    # Create manager pane (last pane)
    run_tmux(["split-window", "-t", f"{session}:{window}", "-v", "-c", str(workspace)])
    run_tmux(["select-layout", "-t", f"{session}:{window}", "tiled"])

    # Build manager command
    manager_cmd = "claude --dangerously-skip-permissions"
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


def stop_swarm() -> None:
    """Stop the swarm gracefully."""
    config = load_config()
    session = config["tmux_session"]

    # Kill the session
    run_tmux(["kill-session", "-t", session], check=False)

    # Clean up lock files
    locks_dir = get_hyperclaude_dir() / "locks"
    if locks_dir.exists():
        for lock_file in locks_dir.glob("*.lock"):
            lock_file.unlink()
