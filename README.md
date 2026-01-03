# hyperclaude

Swarm orchestration for [Claude Code](https://github.com/anthropics/claude-code) — coordinate multiple Claude instances for parallel task execution.

## Quick Install

**macOS:**
```bash
git clone https://github.com/watchthelight/hyperclaude.git && cd hyperclaude && python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

**Linux:**
```bash
git clone https://github.com/watchthelight/hyperclaude.git && cd hyperclaude && python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

After installation, run `hyperclaude setup` to configure Claude Code permissions (done automatically on first swarm start).

## What is hyperclaude?

hyperclaude creates a tmux-based swarm of Claude Code instances: one **manager** that coordinates work, and multiple **workers** that execute tasks in parallel. Supports up to 50 workers with optimized grid layouts.

```
┌─────────────────────────────────────────────────────────────┐
│ tmux session: swarm                                         │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────┤
│ Worker 0 │ Worker 1 │ Worker 2 │ Worker 3 │ Worker 4 │ W 5  │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────┤
│ Manager (coordinates all workers)                           │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- macOS or Linux
- Python 3.10+
- [tmux](https://github.com/tmux/tmux)
- [Claude Code CLI](https://github.com/anthropics/claude-code)

**Linux users**: Requires a supported terminal emulator (gnome-terminal, konsole, xfce4-terminal, alacritty, kitty, or xterm).

## Usage

```bash
# Start swarm in current directory (default: 6 workers, Opus model)
hyperclaude

# Start with custom worker count (up to 50)
hyperclaude --workers 25

# Use different models
hyperclaude --sonnet           # Use Sonnet
hyperclaude --haiku            # Use Haiku

# Start in a specific directory
hyperclaude -d /path/to/project

# Multi-session support (run multiple independent swarms)
hyperclaude --name frontend    # Start named session
hyperclaude --name backend     # Start another session
hyperclaude sessions           # List all sessions

# Stop the swarm
hyperclaude stop
hyperclaude stop --name frontend  # Stop specific session
```

A Terminal window will open with the swarm. The manager (bottom pane) is ready to receive your instructions.

## Protocols

hyperclaude uses a token-efficient protocol system. Workers read protocol docs from `~/.hyperclaude/protocols/`:

- **default** - Basic task execution
- **git-branch** - Workers on separate branches, manager merges
- **search** - Parallel codebase search
- **review** - Code review workflow

Set protocol: `hyperclaude protocol git-branch`

## Manager Commands

The manager uses these commands to coordinate workers:

```bash
hyperclaude send 0 "task"         # Send task to worker 0
hyperclaude broadcast "task"      # Send task to ALL workers
hyperclaude await all-done        # Wait for all workers to complete
hyperclaude state                 # View worker states
hyperclaude results               # View worker results
hyperclaude clear                 # Reset state for next batch
```

## Worker Commands

Workers signal completion and manage file locks:

```bash
hyperclaude done --result "summary"   # Signal task complete
hyperclaude done --error "message"    # Signal error
hyperclaude lock path/to/file.py      # Claim file lock (atomic)
hyperclaude unlock                    # Release locks
```

## How It Works

1. You give the manager a task
2. Manager sets a protocol and delegates subtasks to workers
3. Workers execute in parallel and signal completion with `hyperclaude done`
4. Manager waits with `hyperclaude await all-done` and aggregates results

## Features

- **Scalable**: Supports up to 50 workers with optimized grid layouts
- **Multi-session**: Run multiple independent swarms simultaneously
- **Atomic file locking**: Prevents worker conflicts with fcntl-based locks
- **Dynamic timeouts**: Automatically adjusts for worker count
- **Input validation**: Session names, paths, and message sizes validated
- **Session-aware**: All commands respect the active session context

## License

MIT
