"""Tmux session management for HyperClaude swarm."""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .config import load_config, get_hyperclaude_dir, init_hyperclaude


def run_tmux(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a tmux command."""
    cmd = ["tmux"] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


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
    return '''You are the MANAGER in a HyperClaude swarm. You coordinate {num_workers} worker Claude instances.

## Your Workers

Workers run in tmux panes swarm:main.0 through swarm:main.{worker_range}:
- Workers are in panes 0 through {num_workers_minus_one}
- You (manager) are in pane {num_workers}

## Commands

**Send a task to a worker:**
```bash
tmux send-keys -t swarm:main.N "your task here" && tmux send-keys -t swarm:main.N Enter
```
(Replace N with worker number 0-{num_workers_minus_one})

**Read worker output:**
```bash
tmux capture-pane -t swarm:main.N -p -S -30
```

**Clear a worker's context:**
```bash
tmux send-keys -t swarm:main.N "/clear" && tmux send-keys -t swarm:main.N Enter
```

**Clear ALL workers:**
```bash
bash -c 'for i in {worker_list}; do tmux send-keys -t swarm:main.$i "/clear" && tmux send-keys -t swarm:main.$i Enter; done'
```

**Check worker results:**
```bash
cat ~/.hyperclaude/results/worker-N.txt
```

## Worker Task Protocol

When sending tasks to workers, ALWAYS prefix with this preamble (replacing N with the worker number):

```
You are Worker N in a HyperClaude swarm.

PROTOCOL:
1. Complete the task autonomously
2. Write your result to ~/.hyperclaude/results/worker-N.txt in this format:
   STATUS: COMPLETE
   TASK: <brief task description>
   RESULT:
   <your detailed findings/output>
   FILES_MODIFIED:
   - file1.py
   - file2.py
3. Before editing files, check ~/.hyperclaude/locks/ for conflicts
4. Create ~/.hyperclaude/locks/worker-N.lock listing files you're editing
5. Delete your lock file when done

TASK:
<actual task here>
```

## Best Practices

1. **Clear workers** before assigning new unrelated tasks
2. **Assign non-overlapping work** - different workers should work on different files
3. **Poll for completion** - check ~/.hyperclaude/results/ for worker outputs
4. **Aggregate results** - synthesize outputs from all workers
5. **Handle conflicts** - if two workers need the same file, serialize their tasks

## File Locking

Workers should create lock files before editing:
- Worker creates: ~/.hyperclaude/locks/worker-N.lock
- Lock file contains list of files being edited
- Worker deletes lock file when done
- Before editing, check other workers' lock files for conflicts

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

    # Start Claude in pane 0
    run_tmux(["send-keys", "-t", f"{session}:{window}", f"claude --dangerously-skip-permissions", "Enter"])

    # Create remaining worker panes (1 to num_workers-1)
    for i in range(1, num_workers):
        run_tmux(["split-window", "-t", f"{session}:{window}", "-h", "-c", str(workspace)])
        run_tmux(["send-keys", "-t", f"{session}:{window}", f"claude --dangerously-skip-permissions", "Enter"])
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
    run_tmux(["send-keys", "-t", manager_pane, manager_cmd, "Enter"])

    # Wait for Claude instances to start
    time.sleep(3)

    # Inject manager preamble as first message
    preamble = get_manager_preamble(num_workers, workspace)

    # Write preamble to a temp file and send it
    preamble_file = get_hyperclaude_dir() / "manager-init.txt"
    preamble_file.write_text(preamble)

    # Send the preamble to manager
    # We'll send it as the first user message
    run_tmux(["send-keys", "-t", manager_pane, f"Read ~/.hyperclaude/manager-init.txt and acknowledge you understand your role as swarm manager. Then await my instructions."])
    run_tmux(["send-keys", "-t", manager_pane, "Enter"])

    print(f"\nHyperClaude swarm started!")
    print(f"  Session: {session}")
    print(f"  Workers: {num_workers} (panes 0-{num_workers-1})")
    print(f"  Manager: pane {num_workers}")
    print(f"\nTo attach: tmux attach -t {session}")
    print(f"To stop:   hyperclaude stop")


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
