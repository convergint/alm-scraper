# RFC: Search by Defect ID

**Status:** Implemented  
**Author:** Brian  
**Created:** 2026-02-04

## Summary

Allow searching for defects by ID in the web UI search box. Currently, typing "993" doesn't find defect #993 because the ID field isn't included in the full-text search index.

## Problem

Users often know a defect ID and want to quickly navigate to it. Current workarounds:

1. Use `g d` keyboard shortcut and type the ID (works, but not discoverable)
2. Modify the URL manually to `/defects/993`
3. Use `alm show 993` in the CLI

The search box is the most intuitive place to look up a defect by ID, but it doesn't work:

```
Search: "993"
Results: (empty, or unrelated matches containing "993" in text)
```

## Proposed Solution

Detect when the search query is a numeric ID and include exact ID matches in results.

### User Experience

**Before:**

```
Search: "993"
Results: 0 defects found
```

**After:**

```
Search: "993"
Results: 1 defect found
  #993: Login timeout on SSO redirect
```

**Mixed queries should still work:**

```
Search: "993 oracle"
Results: Defects matching "oracle" in text, plus #993 if it exists
```

### Behavior

1. If query is purely numeric (e.g., "993"), return exact ID match if exists
2. If query contains numbers mixed with text, do normal FTS search
3. ID matches should appear first in results
4. Partial ID matching is NOT supported (searching "99" won't match #993)

## Implementation Details

### Option A: Handle in `search_defects()` function

Modify `db.py:search_defects()` to detect numeric queries:

```python
def search_defects(query: str, limit: int = 50) -> list[Defect]:
    results = []

    # Check for exact ID match
    if query.strip().isdigit():
        defect = get_defect_by_id(int(query.strip()))
        if defect:
            results.append(defect)
            limit -= 1

    # Continue with FTS search
    # ... existing FTS logic ...

    return results
```

### Option B: Handle in API layer

Modify `ui/api.py:get_defects()` to check for ID before calling search:

```python
if q and q.strip().isdigit():
    defect = get_defect_by_id(int(q.strip()))
    if defect:
        return {"defects": [defect.model_dump()], "total": 1, ...}
```

### Recommendation

**Option A** is preferred because:

- Keeps search logic centralized in `db.py`
- Works for both API and any future CLI search
- Allows combining ID match with text results

## Testing Strategy

### Unit Tests

```python
def test_search_by_exact_id():
    """Searching for a numeric ID returns that defect."""
    results = search_defects("993")
    assert len(results) >= 1
    assert results[0].id == 993

def test_search_by_id_not_found():
    """Searching for non-existent ID returns empty."""
    results = search_defects("999999")
    assert len(results) == 0

def test_search_mixed_query():
    """Mixed queries do normal FTS search."""
    results = search_defects("993 oracle")
    # Should search for text, not treat as ID lookup
    assert all("oracle" in (d.name + d.description).lower() for d in results)
```

## Out of Scope

| Item                              | Rationale                         |
| --------------------------------- | --------------------------------- |
| Partial ID matching               | Adds complexity, low value        |
| ID range search (e.g., "990-995") | Over-engineering                  |
| Adding ID to FTS index            | Would pollute text search results |

## Open Questions

1. Should searching "993" also run the FTS search in case there are other relevant matches, or just return the exact ID match?
   - Proposal: Just return exact match for pure numeric queries (simpler, faster)
