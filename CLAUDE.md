# HyperClaude

Swarm orchestration for Claude Code - coordinate multiple Claude instances for parallel task execution.

## Project Structure

```
hyperclaude/
├── pyproject.toml              # Package configuration
├── CLAUDE.md                   # This file
├── swarm.sh                    # Helper script for swarm management
├── launch.sh                   # Legacy launcher (deprecated)
└── hyperclaude/
    ├── __init__.py
    ├── cli.py                  # Click-based CLI entry point
    ├── config.py               # Configuration and directory management
    ├── launcher.py             # Tmux session creation and management
    ├── monitor.py              # Log capture and usage tracking
    └── templates/
        ├── manager-preamble.md # Template for manager initialization
        └── worker-preamble.md  # Template for worker task prefix
```

## Architecture

HyperClaude creates a tmux session with:
- **N Worker panes** (default 6): Independent Claude instances for parallel work
- **1 Manager pane**: Coordinates workers, delegates tasks, aggregates results

```
┌─────────────────────────────────────────────┐
│ tmux session: swarm, window: main           │
├─────────┬─────────┬─────────┬───────────────┤
│ Worker0 │ Worker1 │ ...     │ WorkerN-1     │
├─────────┴─────────┴─────────┴───────────────┤
│ Manager (pane N)                            │
└─────────────────────────────────────────────┘
```

## Key Design Decisions

1. **Workers are stateless**: Cleared before new task batches, receive full context with each task
2. **Manager is stateful**: Can use `--continue` to resume conversations
3. **File-based coordination**: Results in `~/.hyperclaude/results/`, locks in `~/.hyperclaude/locks/`
4. **Separate config**: All HyperClaude data in `~/.hyperclaude/`, doesn't touch target workspaces

## CLI Commands

### User Commands
```bash
hyperclaude                     # Start swarm in current directory
hyperclaude --workers 4         # Start with 4 workers
hyperclaude -d /path/to/proj    # Start in specific directory
hyperclaude stop                # Gracefully shutdown swarm
```

### Manager Commands (for coordinating workers)
```bash
hyperclaude send 0 "task"       # Send task to worker 0
hyperclaude broadcast "task"    # Send task to ALL workers
hyperclaude wait                # Wait for all workers to finish
hyperclaude status              # Show worker status
hyperclaude results             # Show worker results
hyperclaude clear               # Clear all workers
hyperclaude locks               # Show active file locks
```

### Worker Commands (for reporting results)
```bash
hyperclaude report "result" -w 0      # Write result for worker 0
hyperclaude lock file1.py file2.py -w 0  # Claim file locks
hyperclaude unlock -w 0               # Release locks
```

## Development

```bash
# Install in development mode
pip install -e .

# Run CLI
hyperclaude --help
```

## Important Implementation Notes

### tmux send-keys Quirk

The Enter key must be sent as a **separate** tmux command:
```bash
# WRONG - Enter doesn't execute
tmux send-keys -t pane "command" Enter

# CORRECT - Two separate calls
tmux send-keys -t pane "command" && tmux send-keys -t pane Enter
```

### Worker Task Protocol

Workers must be given explicit instructions with each task because they're cleared between batches. The worker preamble template includes:
- Where to write results (`~/.hyperclaude/results/worker-N.txt`)
- Result format (STATUS, TASK, RESULT, FILES_MODIFIED)
- File locking protocol

### Manager Initialization

The manager receives its instructions via prepending to the first user message. It reads `~/.hyperclaude/manager-init.txt` which contains the full protocol documentation.
