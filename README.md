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

## What is hyperclaude?

hyperclaude creates a tmux-based swarm of Claude Code instances: one **manager** that coordinates work, and multiple **workers** that execute tasks in parallel.

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
# Start swarm in current directory
hyperclaude

# Start with custom worker count
hyperclaude --workers 4

# Start in a specific directory
hyperclaude -d /path/to/project

# Stop the swarm
hyperclaude stop
```

A Terminal window will open with the swarm. The manager (bottom pane) is ready to receive your instructions.

## Protocols

hyperclaude uses a token-efficient protocol system. Workers read protocol docs from `~/.hyperclaude/protocols/`:

- **default** - Basic task execution
- **git-branch** - Workers on separate branches, manager merges
- **search** - Parallel codebase search
- **review** - Code review workflow

Set protocol: `hyperclaude protocol git-branch`

## How It Works

1. You give the manager a task
2. Manager sets a protocol and delegates subtasks to workers
3. Workers execute in parallel and signal completion with `hyperclaude done`
4. Manager waits with `hyperclaude await all-done` and aggregates results

## License

MIT
