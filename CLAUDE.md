# hyperclaude

Swarm orchestration for Claude Code - coordinate multiple Claude instances for parallel task execution.

## Project Structure

```
hyperclaude/
├── pyproject.toml              # Package configuration
├── CLAUDE.md                   # This file
└── hyperclaude/
    ├── __init__.py
    ├── cli.py                  # Click-based CLI entry point
    ├── config.py               # Configuration and directory management
    ├── launcher.py             # Tmux session creation and management
    ├── protocols.py            # Protocol and state management
    └── templates/
        └── protocols/          # Default protocol templates
            ├── default.md
            ├── git-branch.md
            ├── search.md
            └── review.md
```

## Architecture

hyperclaude creates a tmux session with:
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

1. **Token-efficient protocols**: Workers read protocol docs from files, not inline prompts
2. **Workers are stateless**: Cleared before new task batches
3. **Manager is interactive**: Uses normal Claude permissions (no bypass)
4. **File-based coordination**: Session state in `~/.hyperclaude/sessions/<name>/`
5. **HYPERCLAUDE_WORKER_ID**: Environment variable auto-set for each worker
6. **Auto-configured permissions**: Adds `Read(~/.hyperclaude/**)` and `Bash(hyperclaude:*)` to `~/.claude/settings.json`
7. **Multi-session support**: Run multiple independent swarms with `--name` flag

## CLI Commands

### Setup & Starting/Stopping
```bash
hyperclaude setup               # Configure Claude Code permissions
hyperclaude setup --check       # Check permission status
hyperclaude                     # Start swarm in current directory
hyperclaude --workers 4         # Start with 4 workers
hyperclaude --name project1     # Start named session (for multiple swarms)
hyperclaude -d /path/to/proj    # Start in specific directory
hyperclaude sessions            # List all registered sessions
hyperclaude stop                # Gracefully shutdown active swarm
hyperclaude stop --name proj1   # Stop specific session
```

### Protocol & Phase Management
```bash
hyperclaude protocol git-branch # Set active protocol
hyperclaude protocol            # Show current protocol
hyperclaude protocols           # List available protocols
hyperclaude phase working       # Set current phase
hyperclaude phase               # Show current phase
```

### Manager Commands (coordinating workers)
```bash
hyperclaude send 0 "task"       # Send task to worker 0
hyperclaude send manager "msg"  # Send message to the manager
hyperclaude broadcast "task"    # Send task to ALL workers
hyperclaude await all-done      # Wait for all workers (trigger-based)
hyperclaude state               # Show worker states (JSON-based)
hyperclaude results             # Show worker results
hyperclaude clear               # Clear all workers and reset state
hyperclaude locks               # Show active file locks
```

### Worker Commands (signaling completion)
```bash
hyperclaude done                      # Signal task complete
hyperclaude done --branch X           # With branch info
hyperclaude done --files a.py b.py    # With modified files
hyperclaude done --error "msg"        # Signal error
hyperclaude lock file1.py file2.py    # Claim file locks
hyperclaude unlock                    # Release locks
```

## State Files

```
~/.hyperclaude/
├── active_session          # Currently active session name
├── protocols/              # Protocol documentation (shared)
│   ├── default.md
│   ├── git-branch.md
│   ├── search.md
│   └── review.md
└── sessions/               # Per-session directories
    └── <session_name>/
        ├── session.json    # Session metadata (workspace, num_workers)
        ├── state/
        │   ├── protocol    # Active protocol name
        │   ├── phase       # Current phase
        │   └── workers/
        │       ├── 0.json  # Worker 0 state (status, branch, files, etc.)
        │       └── ...
        ├── triggers/       # Event files (presence = event occurred)
        │   ├── worker-0-done
        │   ├── all-done
        │   └── ...
        ├── results/        # Worker result files
        └── locks/          # File locks
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

### Worker ID Auto-Detection

Workers have `HYPERCLAUDE_WORKER_ID` environment variable set. Commands like `hyperclaude done` and `hyperclaude lock` auto-detect the worker ID from this.

### Token-Efficient Task Sending

Tasks are sent with minimal preamble:
```
W0 | git-branch | working
Task: Implement user auth
Protocol: ~/.hyperclaude/protocols/git-branch.md
```

Workers read the protocol file for full instructions (once per session).
