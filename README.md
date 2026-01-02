# HyperClaude

Swarm orchestration for [Claude Code](https://github.com/anthropics/claude-code) — coordinate multiple Claude instances for parallel task execution.

## What is HyperClaude?

HyperClaude creates a tmux-based swarm of Claude Code instances: one **manager** that coordinates work, and multiple **workers** that execute tasks in parallel.

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

- macOS
- Python 3.10+
- [tmux](https://github.com/tmux/tmux)
- [Claude Code CLI](https://github.com/anthropics/claude-code)

## Installation

```bash
git clone https://github.com/watchthelight/hyperclaude.git
cd hyperclaude
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

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

A Terminal window will open with the swarm. The manager (bottom pane) is ready to receive your instructions. Just tell it what you want done — it will coordinate the workers automatically.

## How It Works

1. You give the manager a task
2. Manager breaks it down and delegates subtasks to workers
3. Workers execute in parallel and report results
4. Manager aggregates and synthesizes the outputs

The manager understands the full swarm protocol and has CLI tools to coordinate workers efficiently.

## License

MIT
