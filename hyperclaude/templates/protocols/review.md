# Review Protocol

Code review workflow: one worker implements, others review.

## Phases
- **implement** - Primary worker making changes
- **review** - Reviewers examining changes
- **revise** - Primary worker addressing feedback
- **approved** - All reviewers approved
- **done** - Changes merged

## Roles
- **Implementer** (Worker 0): Makes the code changes
- **Reviewers** (Workers 1-N): Review and provide feedback

## Worker Actions

### Implementer (Worker 0)

#### On Initial Task
1. Implement the requested changes
2. Commit with clear description
3. Signal ready for review:
   ```bash
   hyperclaude done --files file1.py file2.py
   ```

#### On Revision Request
1. Read reviewer feedback from results
2. Address each concern
3. Commit fixes
4. Signal ready for re-review:
   ```bash
   hyperclaude done --files file1.py
   ```

### Reviewers (Workers 1-N)

#### On Review Task
1. Read the implementer's changes
2. Check for:
   - Bugs and edge cases
   - Security issues
   - Performance concerns
   - Code style
   - Test coverage
3. Write feedback with specific file:line references
4. Signal with approval status:
   ```bash
   # If approved:
   hyperclaude done

   # If changes needed:
   hyperclaude done --error "Changes requested: [summary]"
   ```

## Manager Actions

### Setup
```bash
hyperclaude protocol review
hyperclaude phase implement
```

### Assign Implementation
```bash
hyperclaude send 0 "Implement feature X"
hyperclaude await worker-0-done
```

### Request Reviews
```bash
hyperclaude phase review
hyperclaude send 1 "Review worker 0's changes to file1.py, file2.py"
hyperclaude send 2 "Review worker 0's changes to file1.py, file2.py"
hyperclaude await all-done
```

### Check Results
```bash
hyperclaude state
# If any worker reported error (changes requested):
hyperclaude results  # See feedback
hyperclaude phase revise
hyperclaude send 0 "Address reviewer feedback: [summary]"
# Repeat review cycle

# If all approved:
hyperclaude phase approved
hyperclaude phase done
hyperclaude clear
```

## State Format
Worker state includes:
- `status`: ready, implementing, reviewing, complete
- `role`: implementer, reviewer
- `approved`: true/false (for reviewers)
- `files`: files being reviewed/modified

## Review Checklist

Reviewers should check:
- [ ] Logic correctness
- [ ] Error handling
- [ ] Input validation
- [ ] Security (injection, auth, etc.)
- [ ] Performance implications
- [ ] Test coverage
- [ ] Documentation updates
- [ ] Code style consistency
