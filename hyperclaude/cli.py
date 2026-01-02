"""CLI entry point for hyperclaude."""

import click
import sys
from pathlib import Path

from .config import load_config, init_hyperclaude
from .launcher import start_swarm, stop_swarm, get_swarm_status, is_swarm_running


@click.group(invoke_without_command=True)
@click.option("--workers", "-w", type=int, help="Number of worker instances")
@click.option("--continue", "-c", "continue_session", is_flag=True, help="Resume manager conversation")
@click.option("--model", "-m", type=str, help="Model to use for all instances")
@click.option("--dir", "-d", "workspace", type=click.Path(exists=True), help="Workspace directory (default: current)")
@click.pass_context
def main(ctx, workers, continue_session, model, workspace):
    """hyperclaude - Swarm orchestration for Claude Code.

    Start a swarm of Claude instances with one manager and multiple workers.
    The manager coordinates task delegation and result aggregation.

    \b
    Examples:
        hyperclaude                    Start swarm in current directory
        hyperclaude --workers 4        Start with 4 workers
        hyperclaude --continue         Resume previous manager session
        hyperclaude -d /path/to/proj   Start in specific directory
        hyperclaude status             Show swarm status
        hyperclaude stop               Stop the swarm
    """
    # If a subcommand is invoked, skip the default behavior
    if ctx.invoked_subcommand is not None:
        return

    # Initialize hyperclaude directories
    init_hyperclaude()

    # Load configuration
    config = load_config()

    # Override with CLI options
    num_workers = workers or config["default_workers"]
    model_name = model or config["default_model"]
    target_workspace = Path(workspace) if workspace else Path.cwd()

    # Check if swarm is already running
    if is_swarm_running():
        click.echo("A swarm is already running. Use 'hyperclaude stop' first, or 'hyperclaude status' to check.")
        sys.exit(1)

    click.echo(f"Starting hyperclaude swarm...")
    click.echo(f"  Workers: {num_workers}")
    click.echo(f"  Model: {model_name}")
    click.echo(f"  Workspace: {target_workspace}")
    click.echo(f"  Continue: {continue_session}")
    click.echo()

    # Start the swarm
    start_swarm(
        workspace=target_workspace,
        num_workers=num_workers,
        model=model_name,
        continue_session=continue_session,
    )


@main.command()
def stop():
    """Stop the running swarm gracefully."""
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    click.echo("Stopping hyperclaude swarm...")
    stop_swarm()
    click.echo("Swarm stopped.")


@main.command()
def status():
    """Show the status of all swarm workers (legacy token-based)."""
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    status_info = get_swarm_status()

    click.echo("hyperclaude Swarm Status")
    click.echo("=" * 40)

    for worker_id, info in status_info.items():
        tokens = info.get("tokens", "?")
        state = info.get("state", "unknown")
        click.echo(f"  Worker {worker_id}: {state} ({tokens} tokens)")

    click.echo("=" * 40)


@main.command()
def clear():
    """Clear all workers' contexts, state, and triggers."""
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    from .launcher import clear_all_workers
    from .protocols import reset_swarm_state

    click.echo("Clearing all workers...")
    clear_all_workers()
    reset_swarm_state()
    click.echo("All workers and state cleared.")


@main.command()
def results():
    """Show latest results from all workers."""
    from .config import get_result_file, load_config

    config = load_config()
    num_workers = config["default_workers"]

    click.echo("Worker Results")
    click.echo("=" * 40)

    for i in range(num_workers):
        result_file = get_result_file(i)
        if result_file.exists():
            content = result_file.read_text().strip()
            # Show first few lines
            lines = content.split("\n")[:5]
            preview = "\n    ".join(lines)
            click.echo(f"Worker {i}:")
            click.echo(f"    {preview}")
            if len(content.split("\n")) > 5:
                click.echo(f"    ... (truncated)")
        else:
            click.echo(f"Worker {i}: No results yet")
        click.echo()


# =============================================================================
# Protocol and Phase Management
# =============================================================================

@main.command()
@click.argument("name", required=False)
def protocol(name):
    """Get or set the active protocol.

    \b
    Examples:
        hyperclaude protocol              Show current protocol
        hyperclaude protocol git-branch   Set active protocol
    """
    from .protocols import get_active_protocol, set_active_protocol, get_protocol, list_protocols

    if name is None:
        # Show current protocol
        current = get_active_protocol()
        if current:
            click.echo(f"Active protocol: {current}")
            click.echo(f"\nProtocol file: ~/.hyperclaude/protocols/{current}.md")
        else:
            click.echo("No protocol set. Use 'hyperclaude protocol <name>' to set one.")
            click.echo(f"Available: {', '.join(list_protocols())}")
    else:
        # Set protocol
        if set_active_protocol(name):
            click.echo(f"Protocol set to: {name}")
        else:
            available = list_protocols()
            click.echo(f"Protocol '{name}' not found.")
            click.echo(f"Available: {', '.join(available)}")


@main.command()
def protocols():
    """List available protocols."""
    from .protocols import list_protocols, get_active_protocol

    available = list_protocols()
    current = get_active_protocol()

    if not available:
        click.echo("No protocols installed. Run 'hyperclaude' once to install defaults.")
        return

    click.echo("Available Protocols")
    click.echo("=" * 40)
    for name in available:
        marker = " (active)" if name == current else ""
        click.echo(f"  {name}{marker}")
    click.echo()
    click.echo("View protocol: cat ~/.hyperclaude/protocols/<name>.md")


@main.command()
@click.argument("name", required=False)
def phase(name):
    """Get or set the current phase.

    \b
    Examples:
        hyperclaude phase             Show current phase
        hyperclaude phase working     Set phase to 'working'
    """
    from .protocols import get_phase, set_phase

    if name is None:
        current = get_phase()
        if current:
            click.echo(f"Current phase: {current}")
        else:
            click.echo("No phase set.")
    else:
        set_phase(name)
        click.echo(f"Phase set to: {name}")


# =============================================================================
# Manager Commands - for coordinating workers
# =============================================================================

@main.command()
@click.argument("worker_id", type=int)
@click.argument("task")
@click.option("--protocol", "-p", "protocol_name", help="Override active protocol")
def send(worker_id, task, protocol_name):
    """Send a task to a specific worker.

    \b
    Examples:
        hyperclaude send 0 "Search for TODO comments"
        hyperclaude send 0 "Implement auth" --protocol git-branch
    """
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    from .launcher import send_to_worker
    from .config import load_config
    from .protocols import (
        get_active_protocol, set_worker_state, get_phase,
        get_protocol_path, set_active_protocol
    )

    config = load_config()
    num_workers = config["default_workers"]

    if worker_id < 0 or worker_id >= num_workers:
        click.echo(f"Invalid worker ID. Must be 0-{num_workers - 1}")
        return

    # Determine protocol
    proto = protocol_name or get_active_protocol() or "default"

    # Set protocol if not already set
    if not get_active_protocol():
        set_active_protocol(proto)

    # Get current phase
    current_phase = get_phase() or "working"

    # Mark worker as working
    set_worker_state(worker_id, status="working", assignment=task)

    # Minimal preamble - references protocol file instead of explaining everything
    protocol_path = get_protocol_path(proto)
    preamble = f"""W{worker_id} | {proto} | {current_phase}
Task: {task}
Protocol: {protocol_path}"""

    send_to_worker(worker_id, preamble)
    click.echo(f"Task sent to worker {worker_id} (protocol: {proto})")


@main.command()
@click.argument("task")
@click.option("--protocol", "-p", "protocol_name", help="Override active protocol")
def broadcast(task, protocol_name):
    """Send the same task to ALL workers.

    \b
    Examples:
        hyperclaude broadcast "Search for security vulnerabilities"
    """
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    from .launcher import send_to_worker
    from .config import load_config
    from .protocols import (
        get_active_protocol, set_worker_state, get_phase,
        get_protocol_path, set_active_protocol
    )

    config = load_config()
    num_workers = config["default_workers"]

    # Determine protocol
    proto = protocol_name or get_active_protocol() or "default"

    # Set protocol if not already set
    if not get_active_protocol():
        set_active_protocol(proto)

    # Get current phase
    current_phase = get_phase() or "working"
    protocol_path = get_protocol_path(proto)

    for i in range(num_workers):
        # Mark worker as working
        set_worker_state(i, status="working", assignment=task)

        # Minimal preamble
        preamble = f"""W{i} | {proto} | {current_phase}
Task: {task}
Protocol: {protocol_path}"""
        send_to_worker(i, preamble)

    click.echo(f"Task broadcast to {num_workers} workers (protocol: {proto})")


@main.command("await")
@click.argument("trigger", default="all-done")
@click.option("--timeout", "-t", default=300, help="Max seconds to wait (default: 300)")
def await_trigger(trigger, timeout):
    """Wait for a trigger (event) to occur.

    \b
    Examples:
        hyperclaude await                  Wait for all-done trigger
        hyperclaude await all-done         Wait for all workers to finish
        hyperclaude await worker-0-done    Wait for specific worker
        hyperclaude await --timeout 60     With custom timeout
    """
    from .protocols import await_trigger as do_await, trigger_exists

    click.echo(f"Waiting for trigger: {trigger}")

    if do_await(trigger, timeout):
        click.echo(f"Trigger '{trigger}' received.")
    else:
        click.echo(f"Timeout waiting for '{trigger}'.")


@main.command()
@click.argument("worker_id", type=int, required=False)
def state(worker_id):
    """View worker state (JSON-based).

    \b
    Examples:
        hyperclaude state       Show all worker states
        hyperclaude state 0     Show state for worker 0
    """
    from .protocols import get_worker_state, get_all_worker_states, get_active_protocol, get_phase
    import json

    # Show protocol/phase header
    proto = get_active_protocol() or "(none)"
    current_phase = get_phase() or "(none)"
    click.echo(f"Protocol: {proto} | Phase: {current_phase}")
    click.echo("=" * 50)

    if worker_id is not None:
        # Single worker
        worker_state = get_worker_state(worker_id)
        click.echo(f"Worker {worker_id}:")
        click.echo(json.dumps(worker_state, indent=2))
    else:
        # All workers
        all_states = get_all_worker_states()
        for wid, wstate in all_states.items():
            status = wstate.get("status", "ready")
            assignment = wstate.get("assignment", "")
            branch = wstate.get("branch", "")
            error = wstate.get("error", "")

            status_str = f"[{status}]"
            if error:
                status_str += f" ERROR: {error}"
            elif branch:
                status_str += f" branch: {branch}"
            elif assignment:
                status_str += f" task: {assignment[:40]}..."

            click.echo(f"  Worker {wid}: {status_str}")


# =============================================================================
# Worker Commands - for workers to signal completion and manage locks
# =============================================================================

@main.command()
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID (auto-detected from env)")
@click.option("--branch", "-b", help="Branch name (for git-branch protocol)")
@click.option("--files", "-f", multiple=True, help="Modified files")
@click.option("--error", "-e", "error_msg", help="Error message if failed")
@click.option("--result", "-r", help="Result summary")
def done(worker, branch, files, error_msg, result):
    """Signal task completion (creates trigger).

    \b
    Examples:
        hyperclaude done                               Signal complete
        hyperclaude done --branch worker-0-feature     With branch info
        hyperclaude done --files src/a.py src/b.py     With modified files
        hyperclaude done --error "Failed to compile"   Signal error
        hyperclaude done --result "Found 5 issues"     With result summary
    """
    from .protocols import (
        set_worker_state, create_trigger, check_all_workers_done,
        get_worker_id_from_env
    )
    from .config import get_result_file

    # Auto-detect worker ID
    if worker is None:
        worker = get_worker_id_from_env()

    if worker is None:
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    # Determine status
    status = "error" if error_msg else "complete"

    # Update worker state
    state_update = {"status": status}
    if branch:
        state_update["branch"] = branch
    if files:
        state_update["files"] = list(files)
    if error_msg:
        state_update["error"] = error_msg
    if result:
        state_update["result"] = result

    set_worker_state(worker, **state_update)

    # Write result file for backwards compatibility
    result_file = get_result_file(worker)
    result_content = f"""STATUS: {status.upper()}
RESULT: {result or error_msg or 'Task completed'}
BRANCH: {branch or 'N/A'}
FILES: {', '.join(files) if files else 'N/A'}
"""
    result_file.write_text(result_content)

    # Create worker done trigger
    create_trigger(f"worker-{worker}-done")
    click.echo(f"Worker {worker} marked as {status}")

    # Check if all workers are done
    if check_all_workers_done():
        click.echo("All workers done - 'all-done' trigger created")


@main.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID")
def lock(files, worker):
    """Claim file locks before editing.

    \b
    Example: hyperclaude lock src/main.py src/utils.py
    """
    from .config import get_lock_file, get_hyperclaude_dir
    from .protocols import get_worker_id_from_env

    if worker is None:
        worker = get_worker_id_from_env()

    if worker is None:
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    # Check for conflicts with other workers' locks
    locks_dir = get_hyperclaude_dir() / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)

    conflicts = []
    for lock_file in locks_dir.glob("*.lock"):
        if lock_file.name == f"worker-{worker}.lock":
            continue
        locked_files = lock_file.read_text().strip().split("\n")
        for f in files:
            if f in locked_files:
                conflicts.append((lock_file.stem, f))

    if conflicts:
        click.echo("CONFLICT: Files locked by other workers:")
        for owner, file in conflicts:
            click.echo(f"  {file} -> {owner}")
        return

    # Create lock file
    lock_file = get_lock_file(worker)
    lock_file.write_text("\n".join(files))
    click.echo(f"Locked {len(files)} file(s)")


@main.command()
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID")
def unlock(worker):
    """Release all file locks held by this worker.

    \b
    Example: hyperclaude unlock
    """
    from .config import get_lock_file
    from .protocols import get_worker_id_from_env

    if worker is None:
        worker = get_worker_id_from_env()

    if worker is None:
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    lock_file = get_lock_file(worker)
    if lock_file.exists():
        lock_file.unlink()
        click.echo("Locks released")
    else:
        click.echo("No locks held")


@main.command()
def locks():
    """Show all active file locks."""
    from .config import get_hyperclaude_dir

    locks_dir = get_hyperclaude_dir() / "locks"

    if not locks_dir.exists():
        click.echo("No locks directory")
        return

    lock_files = list(locks_dir.glob("*.lock"))
    if not lock_files:
        click.echo("No active locks")
        return

    click.echo("Active File Locks")
    click.echo("=" * 40)
    for lock_file in lock_files:
        click.echo(f"\n{lock_file.stem}:")
        for line in lock_file.read_text().strip().split("\n"):
            click.echo(f"  {line}")


if __name__ == "__main__":
    main()
