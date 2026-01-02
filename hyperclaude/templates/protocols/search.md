# Search Protocol

Parallel codebase search with result aggregation.

## Phases
- **searching** - Workers searching assigned areas
- **aggregating** - Manager combining results
- **done** - Search complete

## Worker Actions

### On Task Receipt
1. Search your assigned area/pattern
2. Collect findings (files, line numbers, context)
3. Write detailed results to your result file
4. Signal completion:
   ```bash
   hyperclaude done
   ```

### Result Format
When reporting, include:
- File paths with line numbers
- Relevant code snippets
- Count of matches
- Any patterns noticed

### Example Task
"Search src/api/ for authentication-related code"

Worker should:
1. Search the specified directory
2. Find auth patterns (login, token, session, etc.)
3. Report all findings with context

## Manager Actions

### Setup
```bash
hyperclaude protocol search
hyperclaude phase searching
```

### Distribute Search Tasks
Divide the codebase by:
- Directory (each worker searches different dirs)
- Pattern (each worker searches for different patterns)
- File type (each worker handles different extensions)

```bash
hyperclaude send 0 "Search src/api/ for security vulnerabilities"
hyperclaude send 1 "Search src/models/ for security vulnerabilities"
hyperclaude send 2 "Search src/utils/ for security vulnerabilities"
```

### Aggregate Results
```bash
hyperclaude await all-done
hyperclaude phase aggregating
hyperclaude results   # View all worker findings
# Synthesize and summarize
hyperclaude phase done
hyperclaude clear
```

## Tips

### Good Search Distribution
- Divide by directory structure
- Avoid overlapping searches
- Give clear, specific patterns

### Bad Search Distribution
- Same search to all workers (redundant)
- Overlapping directories (duplicate results)
- Vague queries (inconsistent results)

## State Format
Worker state includes:
- `status`: ready, searching, complete
- `query`: what was searched for
- `matches`: number of matches found
