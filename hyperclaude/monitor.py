"""Background monitoring for HyperClaude swarm."""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_hyperclaude_dir, get_session_log_dir, load_config
from .launcher import capture_pane, get_worker_tokens


def get_usage_file() -> Path:
    """Get the usage tracking file path."""
    return get_hyperclaude_dir() / "usage.json"


def load_usage() -> dict:
    """Load usage data from file."""
    usage_file = get_usage_file()
    if usage_file.exists():
        with open(usage_file) as f:
            return json.load(f)
    return {
        "sessions": [],
        "total_tokens": 0,
    }


def save_usage(usage: dict) -> None:
    """Save usage data to file."""
    usage_file = get_usage_file()
    with open(usage_file, "w") as f:
        json.dump(usage, f, indent=2)


def capture_worker_log(worker_id: int, log_dir: Path) -> None:
    """Capture current worker pane content to log file."""
    log_file = log_dir / f"worker-{worker_id}.log"
    content = capture_pane(worker_id, lines=100)

    # Append with timestamp
    timestamp = datetime.now().isoformat()
    with open(log_file, "a") as f:
        f.write(f"\n--- {timestamp} ---\n")
        f.write(content)
        f.write("\n")


def get_all_worker_tokens(num_workers: int) -> dict[int, Optional[int]]:
    """Get token counts for all workers."""
    return {i: get_worker_tokens(i) for i in range(num_workers)}


def update_usage_tracking(token_counts: dict[int, Optional[int]]) -> None:
    """Update the usage tracking file with current token counts."""
    usage = load_usage()

    # Add current snapshot
    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "workers": {str(k): v for k, v in token_counts.items()},
        "total": sum(v or 0 for v in token_counts.values()),
    }

    # Keep last 100 snapshots
    if "snapshots" not in usage:
        usage["snapshots"] = []
    usage["snapshots"].append(snapshot)
    usage["snapshots"] = usage["snapshots"][-100:]

    # Update total
    usage["total_tokens"] = sum(v or 0 for v in token_counts.values())

    save_usage(usage)


def run_monitor(interval_seconds: int = 5) -> None:
    """Run the monitor loop. Captures logs and tracks usage."""
    config = load_config()
    num_workers = config["default_workers"]
    log_dir = get_session_log_dir()

    print(f"Starting monitor, logging to {log_dir}")
    print(f"Interval: {interval_seconds}s, Workers: {num_workers}")

    try:
        while True:
            # Capture logs from all workers
            for i in range(num_workers):
                try:
                    capture_worker_log(i, log_dir)
                except Exception as e:
                    print(f"Error capturing worker {i}: {e}")

            # Update usage tracking
            try:
                token_counts = get_all_worker_tokens(num_workers)
                update_usage_tracking(token_counts)
            except Exception as e:
                print(f"Error updating usage: {e}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nMonitor stopped.")


def show_usage_summary() -> None:
    """Display a summary of token usage."""
    usage = load_usage()

    print("HyperClaude Usage Summary")
    print("=" * 40)

    if "snapshots" in usage and usage["snapshots"]:
        latest = usage["snapshots"][-1]
        print(f"Last update: {latest['timestamp']}")
        print(f"Current total: {latest['total']} tokens")
        print()
        print("Per-worker tokens:")
        for worker_id, tokens in latest["workers"].items():
            print(f"  Worker {worker_id}: {tokens or 0}")
    else:
        print("No usage data available yet.")

    print()
    print(f"Historical total: {usage.get('total_tokens', 0)} tokens")
