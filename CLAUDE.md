# Snowduck Development Guide

## Collaboration

- Don't assume questions are leading. When asked "should we do X or Y?", evaluate both options on their merits and make a recommendation. Push back if you disagree with a suggestion.
- We're collaborators. Share your reasoning, raise concerns, and suggest alternatives when appropriate.
- We take our engineering seriously and with rigor, but we're casual in tone, you don't have to show deference.

## Git

- Always ask before committing. Don't commit automatically after completing a task.
- When completing an RFC implementation, update its status to "Implemented" in the RFC file.
- Never delete files without asking. Do not assume you are the only one working in this directory.

## Tools

- Use `uv` for Python package management
- Run `make check` after changes (lint + typecheck + fast tests)
- Run `make test` before releasing (all tests including integration)

## Engineering Principles

### Debug before you fix

When something isn't working, resist the urge to guess at solutions. Add observability (logging, --dry-run flags, diagnostic output) to understand the actual problem first. A few minutes of diagnosis saves hours of trial and error.

### Simpler is often better

Prefer straightforward solutions over clever ones. Sequential sync with immediate metadata updates is more reliable than parallel sync with complex merge logic. The performance tradeoff is usually worth it for predictability and maintainability.

### Normalize at the boundary

Validate and normalize inputs when data enters the system, not scattered throughout the code. For example: normalize timestamps to UTC when storing them, not when comparing them later. This prevents entire classes of bugs.

### Make the system observable

Build in tools for understanding what the system will do (--dry-run) and what it did (logging, metadata). Observable systems are easier to trust, debug, and maintain.

### Work incrementally with verification

Plan work in small steps. Run tests and linters after each change. Catch issues early rather than debugging a pile of broken code at the end.

### Test-driven development

Write tests first, then implement in small testable iterations. This workflow works well:

1. **Write a failing test** - Start with the simplest test case that defines the behavior you want
2. **Make it pass** - Write just enough implementation to pass the test (even if ugly)
3. **Add more tests** - Expand coverage with edge cases, error conditions, variations
4. **Keep it passing** - Implement each new test case, running the suite frequently
5. **Refactor** - Once all tests pass and coverage is good, refactor for clarity and maintainability

The key is keeping tests passing throughout. Run `make check` after every small change. Always make sure the docs (README, etc.) are up-to-date before committing. Small testable iterations with a refactoring pass at the end produces better code than trying to write perfect code upfront.

### Property-based testing

Use Hypothesis for property-based tests on pure functions. Properties test invariants that hold for all inputs, catching edge cases that example tests miss.

**Good candidates for property tests:**

- **Idempotence**: `f(f(x)) == f(x)` (e.g., `normalize_sql`)
- **Round-trip**: `reconstruct(parse(x)) == x` (e.g., path parsing)
- **Subset**: `len(filter(xs)) <= len(xs)` (e.g., row filtering)
- **Format invariants**: output always matches a pattern (e.g., SHA256 is 64 hex chars)
- **Ordering**: clauses appear in correct order regardless of input combination

**When to use example tests vs property tests:**

- Use **property tests** for invariants that hold across all valid inputs
- Use **example tests** for specific output formats, exact string matching, or documenting expected behavior for important cases
- Don't write both—a property test for round-trip reconstruction replaces example tests for "parses correctly" and "preserves case"

**Keep tests with their code:**

When extracting functions to a new module, move or consolidate the tests too. Don't leave duplicate tests in the original test file.

### No catch-all modules

Never create `utils.py`, `helpers.py`, or `common.py`. These become dumping grounds that make code hard to find and reason about.

Instead, create domain-specific modules named for what question they answer:

- `env.py` - "What environment am I running in?" (agent detection, terminal info)
- `sql/paths.py` - "How do I parse SQL object paths?" (DATABASE.SCHEMA.TABLE parsing)
- `sql/builders.py` - "How do I build SQL strings?" (pure SQL construction)
- `sql/transforms.py` - "How do I transform query results?" (filtering, formatting)

When you're tempted to add a function to a utils file, ask: "What question does this answer?" Then put it in a module named for that question, or create one.

### Atomic operations, never drop good data

When syncing or modifying data, use atomic operations (temp table + rename) so failures leave the system in a consistent state. Never risk losing good data to save bad data.

### Functional core, imperative shell

Separate pure logic from side effects. Push I/O (database queries, file operations, network calls) to the edges of the system, keeping the core logic pure and testable.

**Pure functions** (the "core"):

- Take inputs, return outputs, no side effects
- Easy to test with simple assertions
- Examples: SQL builders, data transformations, validation, formatting

**Impure functions** (the "shell"):

- Perform I/O: database queries, file reads/writes, API calls
- Orchestrate pure functions and handle side effects
- Live at the boundaries: CLI entry points, command handlers

**In practice:**

```python
# Good: pure function builds SQL, impure function executes it
def build_sample_sql(table: str, rows: int) -> str:  # pure
    return f"SELECT * FROM {table} TABLESAMPLE ({rows} ROWS)"

def run_sample(table: str, rows: int) -> int:  # impure shell
    sql = build_sample_sql(table, rows)  # call pure core
    result = execute_query(conn, sql)     # I/O at the edge
    display_results(result)               # I/O at the edge
    return 0

# Bad: I/O mixed into logic
def build_and_run_query(table: str) -> str:
    result = db.execute(f"SELECT * FROM {table}")  # I/O buried in logic
    return format_result(result)
```

This makes testing easier (test pure functions without mocks), reasoning simpler (side effects are obvious), and refactoring safer (pure functions can be moved/reused freely).

### Stdout is for data, stderr is for humans

CLI commands should write machine-readable output (CSV, JSON, query results) to stdout and human-readable messages (status, progress, errors) to stderr. This allows clean piping (`cmd | head`, `cmd > file.csv`) and makes output parseable by scripts and AI agents.

```python
# Good: data to stdout, status to stderr
console_err = Console(stderr=True)
console_err.print("[green]Query returned 10 rows[/green]")  # stderr
print(csv_output)  # stdout

# Bad: mixing data and status on stdout
print("Running query...")  # corrupts CSV output
print(csv_output)
```
