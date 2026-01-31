# RFC: Query Command

**Status:** Draft  
**Author:** Brian  
**Created:** 2026-01-31

---

## Summary

Add an `alm query` command that executes raw SQL against the defects database. The `--help` output includes the full schema, making it self-documenting for LLMs to construct queries from natural language questions.

## Problem

The `alm list` and `alm stats` commands cover common use cases, but sometimes you need ad-hoc queries:

- "Which defects were closed last week?"
- "What's the average close time per workstream?"
- "Show me all defects mentioning 'invoice' in the description"

Currently you'd need to find the database file and query it manually with `sqlite3`. An LLM assisting a user would need to know the schema to help construct queries.

## Proposed Solution

### User Experience

```bash
# Run a SQL query
$ alm query "SELECT id, name, status FROM defects WHERE priority = 'P1-Critical' LIMIT 5"
id   name                                          status
34   Item description having more than 240 char... Closed
31   E2E Smoke-SDR user is not able to import...   Rejected
32   Assets are not yet configured in the Orac...  Closed

# Get schema and query help (for humans and LLMs)
$ alm query --help
Usage: alm query [OPTIONS] SQL

  Execute a SQL query against the defects database.

  SCHEMA:

  Table: defects
    id              INTEGER PRIMARY KEY  -- Defect ID (e.g., 993)
    name            TEXT                 -- Defect title/summary
    status          TEXT                 -- Open, Closed, Rejected, etc.
    priority        TEXT                 -- P1-Critical, P2-High, P3-Medium, P4-Low
    severity        TEXT                 -- Severity level
    owner           TEXT                 -- Assigned owner (email prefix)
    detected_by     TEXT                 -- Who reported it
    description     TEXT                 -- Plain text description
    description_html TEXT                -- Original HTML description
    dev_comments    TEXT                 -- Plain text dev comments
    dev_comments_html TEXT               -- Original HTML dev comments
    created         TEXT                 -- Creation date (YYYY-MM-DD)
    modified        TEXT                 -- Last modified (YYYY-MM-DD HH:MM:SS)
    closed          TEXT                 -- Close date (YYYY-MM-DD) or NULL
    defect_type     TEXT                 -- Type (01_Code, 02_Configuration, etc.)
    workstream      TEXT                 -- Workstream name
    module          TEXT                 -- Module name
    application     TEXT                 -- Application name
    ...

  Table: defects_fts (full-text search)
    -- FTS5 virtual table for searching name, description, dev_comments
    -- Use: SELECT * FROM defects_fts WHERE defects_fts MATCH 'invoice'

  EXAMPLES:

  # Find defects closed in the last 7 days
  alm query "SELECT id, name, closed FROM defects
             WHERE closed >= date('now', '-7 days') ORDER BY closed DESC"

  # Full-text search for 'invoice'
  alm query "SELECT d.id, d.name, d.status FROM defects d
             JOIN defects_fts f ON d.id = f.rowid
             WHERE defects_fts MATCH 'invoice'"

  # Average close time by workstream
  alm query "SELECT workstream,
                    ROUND(AVG(julianday(closed) - julianday(created)), 1) as avg_days
             FROM defects WHERE closed IS NOT NULL
             GROUP BY workstream ORDER BY avg_days"

Options:
  --csv      Output as CSV
  --json     Output as JSON array
  --help     Show this message and exit.
```

### Command Options

```bash
$ alm query [OPTIONS] SQL

Options:
  --csv      Output as CSV (for piping to other tools)
  --json     Output as JSON array of objects
  --help     Show schema and examples
```

Default output is a simple aligned table (like sqlite3's default).

## Implementation Details

### Schema Documentation

The help text is generated from the actual database schema plus hand-written descriptions. This ensures it stays in sync with the actual table structure.

```python
SCHEMA_DOCS = {
    "id": "Defect ID (e.g., 993)",
    "name": "Defect title/summary",
    "status": "Open, Closed, Rejected, etc.",
    # ...
}

def get_schema_help() -> str:
    """Generate schema documentation from DB + descriptions."""
    # Query sqlite_master for actual columns
    # Merge with SCHEMA_DOCS for descriptions
    # Format as help text
```

### Query Execution

```python
@main.command()
@click.argument("sql")
@click.option("--csv", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def query(sql: str, csv: bool, as_json: bool) -> None:
    """Execute a SQL query against the defects database."""
    db_path = get_db_path()

    if not db_path.exists():
        # error handling

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        if as_json:
            print(format_rows_json(rows, columns))
        elif csv:
            print(format_rows_csv(rows, columns))
        else:
            print(format_rows_table(rows, columns))
    except sqlite3.Error as e:
        err.print(f"[red]SQL Error: {e}[/red]")
        sys.exit(1)
```

### Safety

- Read-only: Only SELECT queries should be allowed
- No writes: Reject INSERT, UPDATE, DELETE, DROP, etc.

```python
def is_safe_query(sql: str) -> bool:
    """Check if query is read-only."""
    normalized = sql.strip().upper()
    return normalized.startswith("SELECT") or normalized.startswith("WITH")
```

## Decisions

1. **Allow EXPLAIN:** Yes, useful for debugging and low risk.

2. **No row limit:** Return all results. User can add LIMIT in SQL if needed.

## Out of Scope

| Item                  | Rationale                                     |
| --------------------- | --------------------------------------------- |
| Interactive SQL shell | Use `sqlite3 $(alm query --db-path)` for that |
| Query history         | Not needed for LLM use case                   |
| Named/saved queries   | Over-engineering for now                      |
