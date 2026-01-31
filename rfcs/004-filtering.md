# RFC: Defect Filtering

**Status:** Draft  
**Author:** Brian  
**Created:** 2026-01-31

---

## Summary

Add an `alm list` command to filter defects by structured fields (status, owner, module, type, etc.). This is distinct from full-text search - filtering is about exact/partial matches on known fields.

## Problem

Currently there's no way to answer questions like:

- "Show me all open defects assigned to me"
- "What defects are in the Data module?"
- "List all P1-Critical defects"
- "Show defects of type 03_Data Error"

You'd have to manually query the SQLite database or scroll through all defects.

## Proposed Solution

Add `alm list` with filter flags for common fields. Filters are AND'd together.

### User Experience

```bash
# List all defects (default: most recently modified first)
$ alm list
#1042  Open     P2-High    Contract sync fails on special chars    david.adkins
#1038  Open     P3-Medium  Missing invoices for site ABCD          prratna
#990   Open     P3-Medium  TCV and Billed Amount Mismatch          david.adkins
...
(showing 50 of 847 defects)

# Filter by status
$ alm list --status open
$ alm list --status closed

# Filter by owner
$ alm list --owner david.adkins
$ alm list --owner me              # special: matches config user if set

# Filter by module
$ alm list --module Data
$ alm list --module "Data Migration"

# Filter by type
$ alm list --type "03_Data Error"

# Filter by priority
$ alm list --priority P1-Critical
$ alm list --priority P2-High

# Combine filters (AND)
$ alm list --status open --module Data --priority P2-High

# Limit results
$ alm list --limit 10
$ alm list -n 10

# Output formats (reuse existing --format flag)
$ alm list --format json
$ alm list --format markdown
```

### Commands / API

```bash
$ alm list --help
Usage: alm list [OPTIONS]

  List defects with optional filtering.

Options:
  -s, --status TEXT    Filter by status (e.g., Open, Closed)
  -o, --owner TEXT     Filter by owner (use 'me' for yourself)
  -m, --module TEXT    Filter by module
  -t, --type TEXT      Filter by defect type
  -p, --priority TEXT  Filter by priority
  -w, --workstream TEXT Filter by workstream
  -n, --limit INT      Maximum results to show [default: 50]
  --all                Show all results (no limit)
  -f, --format TEXT    Output format: table, json, markdown [default: table]
  --help               Show this message and exit.
```

### Output Format

Default table format - compact, scannable:

```
ID      Status   Priority   Name                                    Owner
─────── ──────── ────────── ─────────────────────────────────────── ─────────────
#1042   Open     P2-High    Contract sync fails on special chars    david.adkins
#1038   Open     P3-Medium  Missing invoices for site ABCD          prratna
#990    Open     P3-Medium  TCV and Billed Amount Mismatch          david.adkins

Showing 3 of 3 matches
```

## Implementation Details

### Database Query

Filtering uses SQLite WHERE clauses on the existing defects table:

```python
def list_defects(
    status: str | None = None,
    owner: str | None = None,
    module: str | None = None,
    defect_type: str | None = None,
    priority: str | None = None,
    workstream: str | None = None,
    limit: int = 50,
) -> list[Defect]:
    """List defects with optional filters."""
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if owner:
        conditions.append("owner LIKE ?")
        params.append(f"%{owner}%")
    # ... etc

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""
        SELECT * FROM defects
        WHERE {where}
        ORDER BY priority ASC, created ASC
        LIMIT ?
    """
    params.append(limit)
    # ...
```

### Case Sensitivity

Filters should be case-insensitive for better UX:

- `--status open` matches "Open"
- `--owner DAVID` matches "david.adkins"

Use `LOWER()` or `COLLATE NOCASE` in SQLite.

### Partial Matching

Some fields benefit from partial matching:

- `--owner david` matches "david.adkins_convergint.com"
- `--type Data` matches "03_Data Error"

Use `LIKE %value%` for these.

Exact match for:

- `--status` (Open/Closed are discrete values)
- `--priority` (P1-Critical, P2-High, etc.)

## Open Questions

1. **Interactive selection?** Could integrate with fzf for interactive filtering, but that's probably a separate feature.

## Decisions

1. **Multiple values per filter:** Yes, via repeated flags (e.g., `--status open --status closed`). This is unambiguous, Click supports it natively with `multiple=True`, and it's a familiar pattern from git.

2. **Default sort order:** Priority first (highest to lowest), then oldest to newest within each priority (`ORDER BY priority ASC, created ASC`). This matches a triage workflow - critical items first, longest-waiting items surface. P1-Critical < P2-High < P3-Medium < P4-Low sorts correctly alphabetically.

## Out of Scope

| Item             | Rationale                                                      |
| ---------------- | -------------------------------------------------------------- |
| Full-text search | Separate RFC - uses FTS5, different UX                         |
| Saved filters    | Future enhancement                                             |
| Export to file   | Use shell redirection: `alm list --format json > defects.json` |

## Future Enhancements

1. **Full-text search** - `alm search "invoice balance"` using FTS5
2. **Saved filters** - `alm list --save my-defects` / `alm list @my-defects`
3. **Count only** - `alm list --count` to just show count without listing
