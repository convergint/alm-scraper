# RFC: Local Storage Format

**Status:** Accepted  
**Author:** Brian Brennan  
**Created:** 2025-01-30

---

## Summary

Define how ALM defect data is stored locally for fast lookups and search. We need to support "show me defect 993" and filtering/search across ~3000 defects max.

## Problem

ALM has no linkable URLs. When someone says "check out defect 993", you have to manually navigate the terrible UI to find it. We're scraping the data out, but need to decide how to store it locally for:

1. Fast lookup by ID (`alm show 993`)
2. Search/filter (`alm list --status=Open --owner=jsmith`, full-text search on description)
3. Backup/portability (human-readable export)

## Proposed Solution

Two-layer storage:

1. **JSON file** - canonical backup, human-readable, normalized from ALM's garbage format
2. **SQLite with FTS5** - query layer, rebuilt from JSON on sync

### Why this approach

- JSON is the safety net: portable, diffable, can always rebuild from it
- SQLite gives us indexed lookups + full-text search without loading everything into memory
- At 3k defects, either could work alone, but SQLite makes search fast and JSON keeps us honest

### Storage location

```
~/.local/share/alm-scraper/
├── defects.json -> history/defects-20260130-2253.json
├── defects.db -> history/defects-20260130-2253.db
├── sync_meta.json
└── history/
    ├── defects-20260130-2253.json
    ├── defects-20260130-2253.db
    ├── defects-20260128-1430.json
    ├── defects-20260128-1430.db
    └── ...
```

- `defects.json` and `defects.db` are symlinks to the latest sync in `history/`
- Each sync creates a new timestamped pair of files, preserving full history
- Old syncs are kept forever (or until pruned manually / via future `alm history prune` command)

Why `~/.local/share/` instead of macOS's `~/Library/Application Support/`? Anyone using a CLI tool lives in the terminal and knows where `.local` is. Application Support has spaces in the path and nobody looks there.

Why `sync_meta.json` at the root instead of per-sync or in SQLite? It's a "current state" pointer, not per-sync metadata. The history files are self-describing via their timestamps. `sync_meta.json` answers "what's the current sync?" without chasing symlinks:

```json
{
  "last_sync": "2026-01-30T22:53:00Z",
  "defect_count": 847,
  "current": "history/defects-20260130-2253"
}
```

It's also easier to inspect (`cat sync_meta.json`) than querying SQLite, and survives DB corruption.

Why symlinks instead of hard links? Hard links can confuse backup tools (they look like regular files), don't work across filesystems, and aren't explicit about what they are. Symlinks are obvious.

### Core fields

These fields are guaranteed to exist in the normalized JSON:

| JSON field          | ALM field       | Notes                                   |
| ------------------- | --------------- | --------------------------------------- |
| `id`                | `id`            | integer                                 |
| `name`              | `name`          | defect title                            |
| `status`            | `status`        | Open, Closed, etc.                      |
| `priority`          | `priority`      | P1-Critical, P2-High, P3-Medium, P4-Low |
| `severity`          | `severity`      | similar to priority                     |
| `owner`             | `owner`         | assigned to                             |
| `detected_by`       | `detected-by`   | reporter                                |
| `description`       | `description`   | plain text, HTML stripped               |
| `description_html`  | `description`   | original HTML                           |
| `dev_comments`      | `dev-comments`  | plain text, HTML stripped               |
| `dev_comments_html` | `dev-comments`  | original HTML                           |
| `created`           | `creation-time` | date                                    |
| `modified`          | `last-modified` | datetime                                |
| `closed`            | `closing-date`  | date or null                            |

Additional ALM fields (like `user-template-XX`) will be preserved with cleaned-up names as we discover what's useful during implementation.

### Sync behavior

**Full rebuild with atomic swap:**

1. Delete any stale `.tmp` files from previous failed syncs
2. Fetch all defects from ALM
3. Write `history/defects-{timestamp}.json.tmp` (normalized JSON)
4. Build `history/defects-{timestamp}.db.tmp` (SQLite with FTS5) from the JSON
5. Rename to drop `.tmp` suffix
6. Update symlinks: `defects.json` → new JSON, `defects.db` → new DB
7. Update `sync_meta.json`

If any step fails before the symlinks are updated, the old `defects.json` and `defects.db` symlinks still point to the previous good sync. The tmp files are incomplete artifacts and will be cleaned up on the next sync attempt.

**Why full rebuild instead of incremental?** Simpler, no merge logic, no "what if ALM changed a field we already have" problems. At 3k defects and ~36MB, full rebuild is fast enough.

**Why keep history?**

- **Deleted defects are preserved** - ALM doesn't reliably tell us about deletions. By keeping every sync, defects that disappear from ALM still exist in older snapshots.
- **Time travel** - "What did defect 993 look like last month?" Just query an older DB.
- **Auditability** - Full history of what ALM looked like at each sync.

**Other behaviors:**

- **Ctrl+C is safe** - Incomplete files have `.tmp` suffix, symlinks only update after files are complete.

## Decisions

1. **SQLite over DuckDB** - SQLite is stdlib, FTS5 is battle-tested for text search. DuckDB's strengths (columnar analytics, large dataset aggregations) don't apply here. Can always add `alm export --format=parquet` later if we want to analyze with DuckDB outside the app.

2. **Normalize the JSON** - ALM's `Fields` array format is disgusting. We transform it at the boundary (during sync) into clean, flat objects.

3. **Keep both plain text and HTML** - For fields like `description` and `dev_comments`, store both the stripped plain text (for display/search) and original HTML (preserves formatting). Stripping is lossy; keep the original.

4. **Keep full sync history** - Each sync creates new timestamped files in `history/`. Symlinks point to the latest. This preserves deleted defects and enables time travel queries.

## Alternatives Considered

| Option                      | Pros                               | Cons                                   | Notes                       |
| --------------------------- | ---------------------------------- | -------------------------------------- | --------------------------- |
| JSON only, load into memory | Simple, no deps                    | No FTS, 36MB in RAM                    | Workable at 3k records      |
| SQLite only                 | Single file, fast                  | Binary diffs, rebuild = data loss risk | Need JSON backup anyway     |
| DuckDB                      | Consistent with snowduck, powerful | Heavier dep, overkill for this         | Export option instead       |
| Markdown files              | Human browsable, git-friendly      | Slow search, need index anyway         | Maybe as optional export?   |
| Incremental sync + merge    | Less disk space                    | Complex merge logic, edge cases        | Full rebuild is fast enough |

## Future Enhancements

1. **Parquet export** - `alm export --format=parquet` for DuckDB/pandas analysis
2. **Markdown export** - `alm export --format=markdown` for browsable docs
3. **History pruning** - `alm history prune --keep=10` to clean up old syncs

## Notes

- 100 defects = ~1.2MB JSON (from examples/out.json)
- 3000 defects ≈ 36MB normalized JSON
- Loading 36MB JSON into memory is fine for CLI startup
- At ~40MB per sync (JSON + DB), 100 syncs ≈ 4GB - manageable, but pruning option is nice to have
