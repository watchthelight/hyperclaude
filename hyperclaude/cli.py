"""CLI entry point for hyperclaude."""

import click
import sys
from pathlib import Path

from .config import (
    load_config, init_hyperclaude, get_active_session, set_active_session,
    list_sessions as list_sessions_config, get_session_info,
)
from .launcher import (
    start_swarm, stop_swarm, get_swarm_status, is_swarm_running,
    send_to_manager, is_any_swarm_running,
)


@click.group(invoke_without_command=True)
@click.option("--workers", "-w", type=int, help="Number of worker instances")
@click.option("--continue", "-c", "continue_session", is_flag=True, help="Resume manager conversation")
@click.option("--model", "-m", type=str, help="Model to use for all instances")
@click.option("--dir", "-d", "workspace", type=click.Path(exists=True), help="Workspace directory (default: current)")
@click.option("--name", "-n", "session_name", type=str, help="Session name (for multiple swarms)")
@click.pass_context
def main(ctx, workers, continue_session, model, workspace, session_name):
    """hyperclaude - Swarm orchestration for Claude Code.

    Start a swarm of Claude instances with one manager and multiple workers.
    The manager coordinates task delegation and result aggregation.

    \b
    Examples:
        hyperclaude                    Start swarm in current directory
        hyperclaude --workers 4        Start with 4 workers
        hyperclaude --name project1    Start named session
        hyperclaude --continue         Resume previous manager session
        hyperclaude -d /path/to/proj   Start in specific directory
        hyperclaude sessions           List active sessions
        hyperclaude stop               Stop the swarm
    """
    # Store session name in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["session"] = session_name

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
    name = session_name or "swarm"

    # Stop existing session if running
    if is_swarm_running(name):
        click.echo(f"Stopping existing session '{name}'...")
        stop_swarm(name)

    click.echo(f"Starting hyperclaude swarm...")
    click.echo(f"  Session: {name}")
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
        session_name=name,
    )


@main.command()
@click.option("--name", "-n", "session_name", type=str, help="Session name to stop")
@click.pass_context
def stop(ctx, session_name):
    """Stop the running swarm gracefully."""
    session = session_name or ctx.obj.get("session") or get_active_session()

    if not session:
        # No session specified, check for any running
        if not is_any_swarm_running():
            click.echo("No swarm is currently running.")
            return
        session = "swarm"  # Default

    if not is_swarm_running(session):
        click.echo(f"Session '{session}' is not running.")
        return

    click.echo(f"Stopping hyperclaude swarm '{session}'...")
    stop_swarm(session)
    click.echo("Swarm stopped.")


@main.command()
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def status(ctx, session_name):
    """Show the status of all swarm workers (legacy token-based)."""
    session = session_name or ctx.obj.get("session") or get_active_session()

    if not is_swarm_running(session):
        click.echo(f"No swarm is currently running{f' for session {session}' if session else ''}.")
        return

    status_info = get_swarm_status()

    click.echo(f"hyperclaude Swarm Status{f' ({session})' if session else ''}")
    click.echo("=" * 40)

    for worker_id, info in status_info.items():
        tokens = info.get("tokens", "?")
        state = info.get("state", "unknown")
        click.echo(f"  Worker {worker_id}: {state} ({tokens} tokens)")

    click.echo("=" * 40)


@main.command()
def sessions():
    """List all registered hyperclaude sessions."""
    sessions_list = list_sessions_config()
    active = get_active_session()

    if not sessions_list:
        click.echo("No sessions registered.")
        click.echo("Start a swarm with: hyperclaude --name <name>")
        return

    click.echo("hyperclaude Sessions")
    click.echo("=" * 60)

    for sess in sessions_list:
        name = sess.get("name", "unknown")
        workspace = sess.get("workspace", "?")
        num_workers = sess.get("num_workers", "?")
        running = is_swarm_running(name)

        status_str = "running" if running else "stopped"
        active_marker = " (active)" if name == active else ""

        click.echo(f"  {name}{active_marker}: {status_str}")
        click.echo(f"    Workers: {num_workers}")
        click.echo(f"    Workspace: {workspace}")
        click.echo()

    click.echo("=" * 60)
    click.echo("Use --name <session> with commands to target a specific session.")


@main.command()
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def clear(ctx, session_name):
    """Clear swarm state (triggers, worker states). Worker contexts preserved."""
    from .protocols import reset_swarm_state

    session = session_name or ctx.obj.get("session") or get_active_session()

    click.echo(f"Clearing swarm state{f' for session {session}' if session else ''}...")
    reset_swarm_state(session)
    click.echo("Swarm state cleared (worker contexts preserved).")


@main.command()
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def reset(ctx, session_name):
    """Full reset: clear worker contexts, state, triggers, and result files."""
    session = session_name or ctx.obj.get("session") or get_active_session()

    if not is_swarm_running(session):
        click.echo(f"No swarm is currently running{f' for session {session}' if session else ''}.")
        return

    from .launcher import clear_all_workers
    from .protocols import reset_swarm_state
    from .config import get_session_results_dir

    click.echo("Full reset: clearing workers, state, and results...")
    clear_all_workers()
    reset_swarm_state(session)

    # Also clear result files
    results_dir = get_session_results_dir(session)
    if results_dir.exists():
        for f in results_dir.glob("*.txt"):
            f.unlink()

    click.echo("Full reset complete.")


@main.command()
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def results(ctx, session_name):
    """Show latest results from all workers."""
    from .config import get_session_results_dir

    session = session_name or ctx.obj.get("session") or get_active_session()
    session_info = get_session_info(session) if session else None

    if session_info:
        num_workers = session_info.get("num_workers", 6)
    else:
        config = load_config()
        num_workers = config["default_workers"]

    results_dir = get_session_results_dir(session)

    click.echo(f"Worker Results{f' [{session}]' if session else ''}")
    click.echo("=" * 40)

    for i in range(num_workers):
        result_file = results_dir / f"worker-{i}.txt"
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
@click.option("--session", "-s", "session_name", type=str, help="Session name")
@click.pass_context
def protocol(ctx, name, session_name):
    """Get or set the active protocol.

    \b
    Examples:
        hyperclaude protocol              Show current protocol
        hyperclaude protocol git-branch   Set active protocol
    """
    from .protocols import get_active_protocol, set_active_protocol, list_protocols

    session = session_name or ctx.obj.get("session") or get_active_session()

    if name is None:
        # Show current protocol
        current = get_active_protocol(session)
        if current:
            click.echo(f"Active protocol: {current}")
            click.echo(f"\nProtocol file: ~/.hyperclaude/protocols/{current}.md")
        else:
            click.echo("No protocol set. Use 'hyperclaude protocol <name>' to set one.")
            click.echo(f"Available: {', '.join(list_protocols())}")
    else:
        # Set protocol
        if set_active_protocol(name, session):
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
@click.option("--session", "-s", "session_name", type=str, help="Session name")
@click.pass_context
def phase(ctx, name, session_name):
    """Get or set the current phase.

    \b
    Examples:
        hyperclaude phase             Show current phase
        hyperclaude phase working     Set phase to 'working'
    """
    from .protocols import get_phase, set_phase

    session = session_name or ctx.obj.get("session") or get_active_session()

    if name is None:
        current = get_phase(session)
        if current:
            click.echo(f"Current phase: {current}")
        else:
            click.echo("No phase set.")
    else:
        set_phase(name, session)
        click.echo(f"Phase set to: {name}")


# =============================================================================
# Manager Commands - for coordinating workers
# =============================================================================

def _build_worker_preamble(worker_id: int, protocol: str, phase: str, task: str) -> str:
    """Build minimal task preamble. Worker identity is in system prompt."""
    return f"""[Task for Worker {worker_id}] {protocol} | {phase}

{task}"""


@main.command()
@click.argument("target")
@click.argument("message")
@click.option("--protocol", "-p", "protocol_name", help="Override active protocol")
@click.option("--wait", "-w", is_flag=True, help="Block until worker signals completion")
@click.option("--timeout", "-t", default=300, help="Timeout in seconds when using --wait (default: 300)")
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def send(ctx, target, message, protocol_name, wait, timeout, session_name):
    """Send a message to a worker or the manager.

    TARGET can be a worker number (0-N) or 'manager' to send to the manager.

    \b
    Examples:
        hyperclaude send 0 "Search for TODO comments"
        hyperclaude send manager "Deploy the app"          # Send to manager
        hyperclaude send 0 "Implement auth" --protocol git-branch
        hyperclaude send 0 "Fix bug" --wait                # Block until done
    """
    session = session_name or ctx.obj.get("session") or get_active_session()

    if not is_swarm_running(session):
        click.echo(f"No swarm is currently running{f' for session {session}' if session else ''}.")
        return

    from .launcher import send_to_worker
    from .protocols import (
        get_active_protocol, set_worker_state, get_phase,
        set_active_protocol, await_trigger as do_await,
        get_worker_state, clear_trigger
    )

    # Check if sending to manager
    if target.lower() == "manager":
        send_to_manager(message, session)
        click.echo(f"Message sent to manager")
        return

    # Parse worker ID
    try:
        worker_id = int(target)
    except ValueError:
        click.echo(f"Invalid target '{target}'. Use a worker number (0-N) or 'manager'.")
        return

    session_info = get_session_info(session) if session else None
    if session_info:
        num_workers = session_info.get("num_workers", 6)
    else:
        config = load_config()
        num_workers = config["default_workers"]

    if worker_id < 0 or worker_id >= num_workers:
        click.echo(f"Invalid worker ID. Must be 0-{num_workers - 1}")
        return

    if not message.strip():
        click.echo("Error: Message cannot be empty.")
        return

    # Determine protocol
    proto = protocol_name or get_active_protocol(session) or "default"

    # Set protocol if not already set
    if not get_active_protocol(session):
        set_active_protocol(proto, session)

    # Get current phase
    current_phase = get_phase(session) or "working"

    # Clear any stale trigger for this worker before sending
    clear_trigger(f"worker-{worker_id}-done", session)

    # Mark worker as working
    set_worker_state(worker_id, session, status="working", assignment=message)

    # Build worker preamble with clear instructions
    preamble = _build_worker_preamble(worker_id, proto, current_phase, message)

    send_to_worker(worker_id, preamble, session)
    click.echo(f"Task sent to worker {worker_id} (protocol: {proto})")

    # If --wait flag, block until worker signals done
    if wait:
        trigger_name = f"worker-{worker_id}-done"
        click.echo(f"Waiting for worker {worker_id} to complete (timeout: {timeout}s)...")

        if do_await(trigger_name, timeout, session):
            # Get the worker's final state
            final_state = get_worker_state(worker_id, session)
            status = final_state.get("status", "unknown")
            result = final_state.get("result", "")
            error = final_state.get("error", "")

            if status == "error":
                click.echo(f"Worker {worker_id} finished with ERROR: {error}")
            else:
                click.echo(f"Worker {worker_id} completed: {result or 'Done'}")
        else:
            click.echo(f"Timeout: Worker {worker_id} did not complete within {timeout}s")


@main.command()
@click.argument("task")
@click.option("--protocol", "-p", "protocol_name", help="Override active protocol")
@click.option("--wait", "-w", is_flag=True, help="Block until all workers signal completion")
@click.option("--timeout", "-t", default=300, help="Timeout in seconds when using --wait (default: 300)")
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def broadcast(ctx, task, protocol_name, wait, timeout, session_name):
    """Send the same task to ALL workers.

    \b
    Examples:
        hyperclaude broadcast "Search for security vulnerabilities"
        hyperclaude broadcast "Run tests" --wait              # Block until all done
        hyperclaude broadcast "Run tests" --wait --timeout 60 # With custom timeout
    """
    session = session_name or ctx.obj.get("session") or get_active_session()

    if not is_swarm_running(session):
        click.echo(f"No swarm is currently running{f' for session {session}' if session else ''}.")
        return

    if not task.strip():
        click.echo("Error: Task cannot be empty.")
        return

    from .launcher import send_to_worker
    from .protocols import (
        get_active_protocol, set_worker_state, get_phase,
        set_active_protocol, await_trigger as do_await, get_worker_state,
        clear_all_triggers
    )

    session_info = get_session_info(session) if session else None
    if session_info:
        num_workers = session_info.get("num_workers", 6)
    else:
        config = load_config()
        num_workers = config["default_workers"]

    # Determine protocol
    proto = protocol_name or get_active_protocol(session) or "default"

    # Set protocol if not already set
    if not get_active_protocol(session):
        set_active_protocol(proto, session)

    # Get current phase
    current_phase = get_phase(session) or "working"

    # Clear any stale triggers before sending
    clear_all_triggers(session)

    for i in range(num_workers):
        # Mark worker as working
        set_worker_state(i, session, status="working", assignment=task)

        # Build worker preamble with clear instructions
        preamble = _build_worker_preamble(i, proto, current_phase, task)
        send_to_worker(i, preamble, session)

    click.echo(f"Task broadcast to {num_workers} workers (protocol: {proto})")

    # If --wait flag, block until all workers signal done
    if wait:
        click.echo(f"Waiting for all {num_workers} workers to complete (timeout: {timeout}s)...")

        if do_await("all-done", timeout, session):
            click.echo(f"All workers completed!")

            # Show summary of results
            errors = []
            successes = []
            for i in range(num_workers):
                state = get_worker_state(i, session)
                status = state.get("status", "unknown")
                if status == "error":
                    errors.append((i, state.get("error", "Unknown error")))
                else:
                    successes.append((i, state.get("result", "Done")))

            if successes:
                click.echo(f"\nSuccessful ({len(successes)}):")
                for wid, result in successes:
                    click.echo(f"  Worker {wid}: {result[:60]}{'...' if len(result) > 60 else ''}")

            if errors:
                click.echo(f"\nErrors ({len(errors)}):")
                for wid, error in errors:
                    click.echo(f"  Worker {wid}: {error}")
        else:
            click.echo(f"Timeout: Not all workers completed within {timeout}s")
            # Show which workers are still working
            for i in range(num_workers):
                state = get_worker_state(i, session)
                if state.get("status") == "working":
                    click.echo(f"  Worker {i}: still working")


@main.command("await")
@click.argument("trigger", default="all-done")
@click.option("--timeout", "-t", default=300, help="Max seconds to wait (default: 300)")
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def await_cmd(ctx, trigger, timeout, session_name):
    """Wait for a trigger (event) to occur.

    \b
    Examples:
        hyperclaude await                  Wait for all-done trigger
        hyperclaude await all-done         Wait for all workers to finish
        hyperclaude await worker-0-done    Wait for specific worker
        hyperclaude await --timeout 60     With custom timeout
    """
    from .protocols import await_trigger as do_await

    session = session_name or ctx.obj.get("session") or get_active_session()

    click.echo(f"Waiting for trigger: {trigger}")

    if do_await(trigger, timeout, session):
        click.echo(f"Trigger '{trigger}' received.")
    else:
        click.echo(f"Timeout waiting for '{trigger}'.")


@main.command()
@click.argument("worker_id", type=int, required=False)
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def state(ctx, worker_id, session_name):
    """View worker state (JSON-based).

    \b
    Examples:
        hyperclaude state       Show all worker states
        hyperclaude state 0     Show state for worker 0
    """
    from .protocols import get_worker_state, get_all_worker_states, get_active_protocol, get_phase
    import json

    session = session_name or ctx.obj.get("session") or get_active_session()

    # Show protocol/phase header
    proto = get_active_protocol(session) or "(none)"
    current_phase = get_phase(session) or "(none)"
    session_str = f" [{session}]" if session else ""
    click.echo(f"Protocol: {proto} | Phase: {current_phase}{session_str}")
    click.echo("=" * 50)

    if worker_id is not None:
        # Single worker
        worker_state = get_worker_state(worker_id, session)
        click.echo(f"Worker {worker_id}:")
        click.echo(json.dumps(worker_state, indent=2))
    else:
        # All workers
        all_states = get_all_worker_states(session)
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
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def done(ctx, worker, branch, files, error_msg, result, session_name):
    """Signal task completion (creates trigger).

    \b
    Examples:
        hyperclaude done                                       Signal complete
        hyperclaude done --branch worker-0-feature             With branch info
        hyperclaude done --files a.py --files b.py             With modified files
        hyperclaude done --error "Failed to compile"           Signal error
        hyperclaude done --result "Found 5 issues"             With result summary
    """
    from .protocols import (
        set_worker_state, create_trigger, check_all_workers_done,
        get_worker_id_from_env
    )
    from .config import get_session_results_dir

    session = session_name or ctx.obj.get("session") or get_active_session()

    # Auto-detect worker ID
    if worker is None:
        worker = get_worker_id_from_env()

    if worker is None:
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    # Determine status
    done_status = "error" if error_msg else "complete"

    # Update worker state
    state_update = {"status": done_status}
    if branch:
        state_update["branch"] = branch
    if files:
        state_update["files"] = list(files)
    if error_msg:
        state_update["error"] = error_msg
    if result:
        state_update["result"] = result

    set_worker_state(worker, session, **state_update)

    # Write result file for backwards compatibility
    results_dir = get_session_results_dir(session)
    results_dir.mkdir(parents=True, exist_ok=True)
    result_file = results_dir / f"worker-{worker}.txt"
    result_content = f"""STATUS: {done_status.upper()}
RESULT: {result or error_msg or 'Task completed'}
BRANCH: {branch or 'N/A'}
FILES: {', '.join(files) if files else 'N/A'}
"""
    result_file.write_text(result_content)

    # Create worker done trigger
    create_trigger(f"worker-{worker}-done", session)
    click.echo(f"Worker {worker} marked as {done_status}")

    # Check if all workers are done
    if check_all_workers_done(session):
        click.echo("All workers done - 'all-done' trigger created")


@main.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID")
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def lock(ctx, files, worker, session_name):
    """Claim file locks before editing.

    \b
    Example: hyperclaude lock src/main.py src/utils.py
    """
    from .config import get_session_locks_dir
    from .protocols import get_worker_id_from_env

    session = session_name or ctx.obj.get("session") or get_active_session()

    if worker is None:
        worker = get_worker_id_from_env()

    if worker is None:
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    # Check for conflicts with other workers' locks
    locks_dir = get_session_locks_dir(session)
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
    lock_file = locks_dir / f"worker-{worker}.lock"
    lock_file.write_text("\n".join(files))
    click.echo(f"Locked {len(files)} file(s)")


@main.command()
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID")
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def unlock(ctx, worker, session_name):
    """Release all file locks held by this worker.

    \b
    Example: hyperclaude unlock
    """
    from .config import get_session_locks_dir
    from .protocols import get_worker_id_from_env

    session = session_name or ctx.obj.get("session") or get_active_session()

    if worker is None:
        worker = get_worker_id_from_env()

    if worker is None:
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    lock_file = get_session_locks_dir(session) / f"worker-{worker}.lock"
    if lock_file.exists():
        lock_file.unlink()
        click.echo("Locks released")
    else:
        click.echo("No locks held")


@main.command()
@click.option("--name", "-n", "session_name", type=str, help="Session name")
@click.pass_context
def locks(ctx, session_name):
    """Show all active file locks."""
    from .config import get_session_locks_dir

    session = session_name or ctx.obj.get("session") or get_active_session()
    locks_dir = get_session_locks_dir(session)

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


# =============================================================================
# Setup Commands
# =============================================================================

@main.command()
@click.option("--check", "-c", is_flag=True, help="Only check, don't configure")
def setup(check):
    """Configure Claude Code permissions for hyperclaude.

    Adds pre-authorized permissions to ~/.claude/settings.json:
    - Read(~/.hyperclaude/**) - Read config and protocol files
    - Bash(hyperclaude:*) - Run hyperclaude CLI commands

    \b
    Examples:
        hyperclaude setup          Configure permissions
        hyperclaude setup --check  Check current status
    """
    from .config import configure_claude_permissions, check_claude_permissions, get_claude_settings_path

    if check:
        # Just check status
        perms = check_claude_permissions()
        settings_path = get_claude_settings_path()

        click.echo(f"Claude settings: {settings_path}")
        click.echo("=" * 50)

        all_configured = True
        for perm, configured in perms.items():
            status = "configured" if configured else "NOT configured"
            symbol = "✓" if configured else "✗"
            click.echo(f"  {symbol} {perm}: {status}")
            if not configured:
                all_configured = False

        if all_configured:
            click.echo("\nAll permissions configured.")
        else:
            click.echo("\nRun 'hyperclaude setup' to configure missing permissions.")
    else:
        # Configure permissions
        if configure_claude_permissions():
            click.echo("Claude Code permissions configured successfully!")
            click.echo("\nAdded to ~/.claude/settings.json:")
            click.echo("  - Read(~/.hyperclaude/**)")
            click.echo("  - Bash(hyperclaude:*)")
        else:
            click.echo("Permissions already configured.")


if __name__ == "__main__":
    main()
