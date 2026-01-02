# HyperClaude

Swarm orchestration for [Claude Code](https://github.com/anthropics/claude-code) — coordinate multiple Claude instances for parallel task execution.

## What is HyperClaude?

HyperClaude creates a tmux-based swarm of Claude Code instances: one **manager** that coordinates work, and multiple **workers** that execute tasks in parallel. The manager delegates tasks, the workers complete them autonomously and report results.

```
┌─────────────────────────────────────────────────────────────┐
│ tmux session: swarm                                          │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────┤
│ Worker 0 │ Worker 1 │ Worker 2 │ Worker 3 │ Worker 4 │ W 5  │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────┤
│ Manager (coordinates all workers)                            │
└─────────────────────────────────────────────────────────────┘
```

## Requirements

- macOS or Linux
- Python 3.10+
- [tmux](https://github.com/tmux/tmux)
- [Claude Code CLI](https://github.com/anthropics/claude-code) (`claude` command)

## Installation

```bash
# Clone the repository
git clone https://github.com/watchthelight/hyperclaude.git
cd hyperclaude

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Verify installation
hyperclaude --help
```

### Add to PATH (optional)

To use `hyperclaude` from anywhere, add the virtual environment to your shell:

```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'alias hyperclaude="~/path/to/hyperclaude/.venv/bin/hyperclaude"' >> ~/.zshrc
```

## Usage

### Start a Swarm

```bash
# Start swarm in current directory (6 workers by default)
hyperclaude

# Start with custom worker count
hyperclaude --workers 4

# Start in a specific directory
hyperclaude -d /path/to/project

# Resume manager's previous conversation
hyperclaude --continue
```

### Manage the Swarm

```bash
# Check status of all workers
hyperclaude status

# Clear all workers' contexts
hyperclaude clear

# View worker results
hyperclaude results

# Stop the swarm
hyperclaude stop
```

### Attach to the Swarm

After starting, attach to the tmux session to interact with the manager:

```bash
tmux attach -t swarm
```

The manager pane is at the bottom. Workers are in the top panes.

## How It Works

1. **Manager receives instructions** — When the swarm starts, the manager Claude instance is initialized with the swarm protocol
2. **Manager delegates tasks** — Send the manager a complex task; it breaks it down and assigns subtasks to workers
3. **Workers execute autonomously** — Each worker completes its task and writes results to `~/.hyperclaude/results/worker-N.txt`
4. **Manager aggregates results** — The manager polls result files and synthesizes the outputs

### Worker Protocol

Workers receive tasks with a preamble that instructs them to:
- Complete the task autonomously
- Write structured results to their result file
- Check for file locks before editing shared files
- Create lock files when editing

### File Locations

```
~/.hyperclaude/
├── config.yaml              # Configuration
├── results/
│   └── worker-N.txt         # Worker result files
├── locks/
│   └── worker-N.lock        # File lock claims
└── logs/
    └── session-TIMESTAMP/   # Session logs
```

## Helper Script

The `swarm.sh` script provides convenient shortcuts:

```bash
./swarm.sh clear          # Clear all workers
./swarm.sh clear 2        # Clear worker 2
./swarm.sh send 0 "task"  # Send task to worker 0
./swarm.sh read 0         # Read worker 0 output
./swarm.sh status         # Show all workers
./swarm.sh ready          # Check if workers are ready
./swarm.sh results        # Show all result files
./swarm.sh locks          # Show active file locks
```

## Configuration

Edit `~/.hyperclaude/config.yaml`:

```yaml
default_workers: 6
default_model: claude-sonnet-4-20250514
log_retention_days: 7
poll_interval_seconds: 5
```

## Tips

- **Clear before new work** — Always clear workers before starting unrelated tasks
- **Divide by file** — Assign different workers to different files/directories to avoid conflicts
- **Use file locking** — Workers should create lock files before editing shared resources
- **Poll results** — Check `~/.hyperclaude/results/` to know when workers finish

## License

MIT
