"""CLI entry point for HyperClaude."""

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
    """HyperClaude - Swarm orchestration for Claude Code.

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

    # Initialize HyperClaude directories
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

    click.echo(f"Starting HyperClaude swarm...")
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

    click.echo("Stopping HyperClaude swarm...")
    stop_swarm()
    click.echo("Swarm stopped.")


@main.command()
def status():
    """Show the status of all swarm workers."""
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    status_info = get_swarm_status()

    click.echo("HyperClaude Swarm Status")
    click.echo("=" * 40)

    for worker_id, info in status_info.items():
        tokens = info.get("tokens", "?")
        state = info.get("state", "unknown")
        click.echo(f"  Worker {worker_id}: {state} ({tokens} tokens)")

    click.echo("=" * 40)


@main.command()
def clear():
    """Clear all workers' contexts."""
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    from .launcher import clear_all_workers
    click.echo("Clearing all workers...")
    clear_all_workers()
    click.echo("All workers cleared.")


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
# Manager Commands - for coordinating workers
# =============================================================================

@main.command()
@click.argument("worker_id", type=int)
@click.argument("task")
def send(worker_id, task):
    """Send a task to a specific worker.

    Example: hyperclaude send 0 "Search for TODO comments"
    """
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    from .launcher import send_to_worker
    from .config import load_config

    config = load_config()
    num_workers = config["default_workers"]

    if worker_id < 0 or worker_id >= num_workers:
        click.echo(f"Invalid worker ID. Must be 0-{num_workers - 1}")
        return

    # Add worker preamble to task
    preamble = f"""You are Worker {worker_id} in a HyperClaude swarm.

PROTOCOL:
1. Complete the task autonomously
2. When done, run: hyperclaude report "your result summary"
3. If editing files, first run: hyperclaude lock file1.py file2.py
4. When done editing, run: hyperclaude unlock

TASK:
{task}"""

    send_to_worker(worker_id, preamble)
    click.echo(f"Task sent to worker {worker_id}")


@main.command()
@click.argument("task")
def broadcast(task):
    """Send the same task to ALL workers.

    Example: hyperclaude broadcast "Search for security vulnerabilities"
    """
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    from .launcher import send_to_worker
    from .config import load_config

    config = load_config()
    num_workers = config["default_workers"]

    for i in range(num_workers):
        preamble = f"""You are Worker {i} in a HyperClaude swarm.

PROTOCOL:
1. Complete the task autonomously
2. When done, run: hyperclaude report "your result summary"
3. If editing files, first run: hyperclaude lock file1.py file2.py
4. When done editing, run: hyperclaude unlock

TASK:
{task}"""
        send_to_worker(i, preamble)

    click.echo(f"Task broadcast to {num_workers} workers")


@main.command()
@click.option("--timeout", "-t", default=300, help="Max seconds to wait (default: 300)")
def wait(timeout):
    """Wait for all workers to be idle (0 tokens).

    Useful after sending tasks to wait for completion.
    """
    if not is_swarm_running():
        click.echo("No swarm is currently running.")
        return

    import time
    from .launcher import get_worker_tokens
    from .config import load_config

    config = load_config()
    num_workers = config["default_workers"]

    click.echo("Waiting for workers to complete...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        all_idle = True
        for i in range(num_workers):
            tokens = get_worker_tokens(i)
            if tokens is None or tokens > 0:
                all_idle = False
                break

        if all_idle:
            click.echo("All workers idle.")
            return

        time.sleep(2)

    click.echo("Timeout waiting for workers.")


# =============================================================================
# Worker Commands - for workers to report results and manage locks
# =============================================================================

@main.command()
@click.argument("result")
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID (auto-detected if set)")
@click.option("--status", "-s", default="COMPLETE", help="Status: COMPLETE, ERROR, PARTIAL")
@click.option("--task", "-t", default="", help="Task description")
def report(result, worker, status, task):
    """Write a result to the worker's result file.

    Example: hyperclaude report "Found 5 TODO comments in src/"
    """
    from .config import get_result_file

    if worker is None:
        # Try to detect worker ID from environment or prompt
        click.echo("Error: Worker ID required. Use --worker N or set HYPERCLAUDE_WORKER_ID")
        return

    result_file = get_result_file(worker)

    content = f"""STATUS: {status}
TASK: {task or 'Not specified'}
RESULT:
{result}
FILES_MODIFIED:
(none reported)
"""

    result_file.write_text(content)
    click.echo(f"Result written to {result_file}")


@main.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--worker", "-w", type=int, envvar="HYPERCLAUDE_WORKER_ID", help="Worker ID")
def lock(files, worker):
    """Claim file locks before editing.

    Example: hyperclaude lock src/main.py src/utils.py
    """
    from .config import get_lock_file, get_hyperclaude_dir

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

    Example: hyperclaude unlock
    """
    from .config import get_lock_file

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
