# RFC: Stats Command

**Status:** Draft  
**Author:** Brian  
**Created:** 2026-01-31

---

## Summary

Add an `alm stats` command to show aggregate statistics about the defect backlog - counts by status, priority, module, owner, etc. Quick visibility into the state of things without writing SQL.

## Problem

To answer questions like "how many open P1s do we have?" or "who has the most defects assigned?" you'd need to query the SQLite database directly. That's not user-friendly and breaks the abstraction of the CLI.

## Proposed Solution

A simple `alm stats` command that runs aggregate queries and displays a summary.

### User Experience

```
$ alm stats

Defects: 127 open / 1136 closed (1263 total)

Oldest open:  #417 (2025-08-15) - Purchase Order - Missing data...
Close time:   p50: 3d | p90: 14d | avg: 7d

By Priority (open):
  P1-Critical      5  (4%)
  P2-High         23  (18%)
  P3-Medium       89  (70%)
  P4-Low          10  (8%)

By Module (open, top 5):
  Data            45  (35%)
  Integration     32  (25%)
  UI              28  (22%)
  Reports         15  (12%)
  Other            7  (6%)

By Owner (open, top 5):
  david.adkins    18  (14%)
  prratna         15  (12%)
  jenn.hilber     12  (9%)
  antfoster        9  (7%)
  sagmaru          8  (6%)

By Type (open, top 5):
  03_Data Error   42  (33%)
  02_Functional   35  (28%)
  01_Integration  28  (22%)
  04_UI           15  (12%)
  05_Performance   7  (6%)

By Workstream (open, top 5):
  Convergint      85  (67%)
  Migration       22  (17%)
  Integration     12  (9%)
  Testing          5  (4%)
  Other            3  (2%)
```

### Command Options

```bash
$ alm stats --help
Usage: alm stats [OPTIONS]

  Show aggregate statistics about defects.

Options:
  --all         Include closed defects in breakdowns (default: open only)
  --top N       Number of items to show in each breakdown [default: 5]
  --json        Output as JSON
  --help        Show this message and exit.
```

By default, breakdowns show open defects only (matching `alm list` behavior). Use `--all` to include closed.

## Implementation Details

### Database Queries

Simple GROUP BY queries:

```python
def get_stats(include_closed: bool = False) -> Stats:
    status_filter = "" if include_closed else "WHERE LOWER(status) = 'open'"

    # Total counts
    total = query("SELECT COUNT(*) FROM defects")
    open_count = query("SELECT COUNT(*) FROM defects WHERE LOWER(status) = 'open'")
    closed_count = total - open_count

    # By priority
    by_priority = query(f"""
        SELECT priority, COUNT(*) as count
        FROM defects {status_filter}
        GROUP BY priority
        ORDER BY priority ASC
    """)

    # By module (top 5)
    by_module = query(f"""
        SELECT module, COUNT(*) as count
        FROM defects {status_filter}
        GROUP BY module
        ORDER BY count DESC
        LIMIT 5
    """)

    # Similar for owner, type...
```

### Output Format

Default: human-readable table with Rich formatting
`--json`: machine-readable for scripting

```json
{
  "total": 1263,
  "open": 127,
  "closed": 1136,
  "by_priority": {"P1-Critical": 5, "P2-High": 23, ...},
  "by_module": {"Data": 45, "Integration": 32, ...},
  "by_owner": {"david.adkins": 18, "prratna": 15, ...},
  "by_type": {"03_Data Error": 42, ...}
}
```

## Decisions

1. **Breakdowns to include:** Priority, module, owner, type, and workstream.

2. **Top N configurable:** Default to 5, add `--top N` flag to customize.

3. **Show percentages:** Yes, display as "Data: 45 (35%)" - try it and see how it looks.

4. **Summary stats:** Show oldest open ticket and close time percentiles (p50, p90, avg) at the top.

## Out of Scope

| Item              | Rationale                                             |
| ----------------- | ----------------------------------------------------- |
| Historical trends | Would need to track stats over time, separate feature |
| Charts/graphs     | CLI isn't the right medium                            |
| Drill-down        | Use `alm list --module Data` for that                 |
