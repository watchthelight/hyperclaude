# Default Protocol

Basic task execution without git branching.

## Phases
- **working** - Workers executing tasks
- **done** - All tasks complete

## Worker Actions

### On Task Receipt
1. Execute the assigned task
2. If editing files, lock first: `hyperclaude lock file1.py file2.py`
3. Complete the work
4. Release locks: `hyperclaude unlock`
5. Signal completion: `hyperclaude done --files file1.py file2.py`

### On Conflict
If a file you need is locked by another worker:
```bash
hyperclaude done --error "File X locked by worker N"
```

## Manager Actions

### After Sending Tasks
1. Wait for completion: `hyperclaude await all-done`
2. Check results: `hyperclaude state`
3. View detailed output: `hyperclaude results`
4. Clear for next batch: `hyperclaude clear`

## Commands Reference

| Command | Description |
|---------|-------------|
| `hyperclaude done` | Signal task complete |
| `hyperclaude done --error "msg"` | Signal error |
| `hyperclaude done --files a.py b.py` | Report modified files |
| `hyperclaude lock file.py` | Claim file lock |
| `hyperclaude unlock` | Release locks |
| `hyperclaude locks` | View active locks |
