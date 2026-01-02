# Git Branch Protocol

Each worker operates on an isolated git branch. Manager merges when all complete.

## Phases
- **assign** - Manager distributing tasks
- **working** - Workers implementing on branches
- **complete** - Workers have pushed branches
- **merging** - Manager merging branches
- **done** - All merged to main

## Worker Actions

### On Task Receipt
1. Create feature branch:
   ```bash
   git checkout -b worker-{id}-{task-slug}
   ```
2. Implement the task
3. Commit changes:
   ```bash
   git add .
   git commit -m "Worker {id}: {description}"
   ```
4. Push branch:
   ```bash
   git push -u origin worker-{id}-{task-slug}
   ```
5. Signal completion:
   ```bash
   hyperclaude done --branch worker-{id}-{task-slug}
   ```

### On Conflict
If you encounter merge conflicts while working:
```bash
hyperclaude done --error "Conflict in file X"
```

### Important
- Never work directly on main/master
- Each worker gets their own branch
- Don't merge - manager handles that

## Manager Actions

### Setup
```bash
hyperclaude protocol git-branch
hyperclaude phase assign
```

### Distribute Tasks
```bash
hyperclaude send 0 "Implement feature A"
hyperclaude send 1 "Implement feature B"
hyperclaude phase working
```

### Wait and Merge
```bash
hyperclaude await all-done
hyperclaude phase merging

# For each worker branch:
git merge worker-0-feature-a
git merge worker-1-feature-b
# Resolve any conflicts

hyperclaude phase done
hyperclaude clear
```

## State Format
Worker state includes:
- `status`: ready, working, complete, error
- `branch`: the worker's branch name
- `files`: list of modified files
- `error`: error message if failed

## Commands Reference

| Command | Description |
|---------|-------------|
| `hyperclaude done --branch X` | Signal complete with branch name |
| `hyperclaude state` | View all worker states |
| `hyperclaude await all-done` | Wait for all workers |
| `hyperclaude phase X` | Set current phase |
