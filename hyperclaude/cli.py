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


if __name__ == "__main__":
    main()
