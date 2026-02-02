# RFC: Kanban View

**Status:** Draft  
**Author:** Brian  
**Created:** 2026-02-01

## Pre-Submission Checklist

- [x] **Examples show real output** - Including mockups of the kanban layout
- [x] **No surprises** - Behavior is predictable and documented

---

## Summary

Add a read-only kanban board view to the web UI that displays defects as cards organized by status columns. Users can customize horizontal swimlanes (rows) to group defects by priority, owner, module, or other fields.

## Problem

The current list view shows defects in a flat table, which makes it hard to:

- Visualize the distribution of work across different statuses at a glance
- See bottlenecks (e.g., too many items stuck in "Blocked" or "Retest")
- Understand workflow progress without mentally grouping items

Teams commonly use kanban boards to visualize work-in-progress and identify flow problems. ALM's native interface doesn't offer this view either.

## Proposed Solution

Add a `/kanban` route to the web UI that renders defects as cards in columns, where each column represents a status. Users can optionally enable swimlanes to group cards vertically by a chosen field.

### User Experience

**Default view (no swimlanes):**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  New (12)      │  Open (34)     │  In Progress (8) │  Retest (5)  │  Blocked (3)  │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────┐  │ ┌───────────┐  │ ┌───────────┐    │ ┌─────────┐  │ ┌─────────┐   │
│ │ #1042     │  │ │ #993      │  │ │ #1001     │    │ │ #987    │  │ │ #1015   │   │
│ │ P1-Crit   │  │ │ P2-High   │  │ │ P2-High   │    │ │ P3-Med  │  │ │ P1-Crit │   │
│ │ Login...  │  │ │ SSO tim.. │  │ │ Data mi.. │    │ │ Report..│  │ │ API bl..│   │
│ └───────────┘  │ └───────────┘  │ └───────────┘    │ └─────────┘  │ └─────────┘   │
│ ┌───────────┐  │ ┌───────────┐  │ ┌───────────┐    │ ┌─────────┐  │ ┌─────────┐   │
│ │ #1044     │  │ │ #1002     │  │ │ #1010     │    │ │ #1003   │  │ │ #1022   │   │
│ │ ...       │  │ │ ...       │  │ │ ...       │    │ │ ...     │  │ │ ...     │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**With swimlanes by priority:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [Swimlane: Priority ▼]                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  P1-Critical                                                                │
│  ───────────────────────────────────────────────────────────────────────────│
│  New (2)       │  Open (5)      │  In Progress (1) │  Blocked (2)           │
│  ┌─────────┐   │  ┌─────────┐   │  ┌─────────┐     │  ┌─────────┐           │
│  │ #1042   │   │  │ #993    │   │  │ #1001   │     │  │ #1015   │           │
│  └─────────┘   │  └─────────┘   │  └─────────┘     │  └─────────┘           │
├─────────────────────────────────────────────────────────────────────────────┤
│  P2-High                                                                    │
│  ───────────────────────────────────────────────────────────────────────────│
│  New (4)       │  Open (12)     │  In Progress (3) │  Blocked (1)           │
│  ...           │  ...           │  ...             │  ...                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Navigation

- Accessible via nav link or keyboard shortcut `g b` (go board)
- Cards are clickable, linking to defect detail view
- Keyboard navigation: arrow keys to move between cards, Enter to open

### Layout

- Horizontal scroll to accommodate 9+ columns (cards need readable width)
- Sticky first column: "Blocked" stays pinned on the left while scrolling
- Sticky header row: column headers scroll horizontally with content but stay pinned vertically (swimlane headers scroll normally)
- Arrow key navigation auto-scrolls to keep focused card visible

### Card Design

- Title truncated to 2 lines (CSS `line-clamp`)
- No in-place expansion; click navigates to detail view
- Shows: ID, priority badge, truncated title, owner initials

### URL Structure

```
/kanban                           # Default: no swimlanes
/kanban?lane=priority             # Swimlanes by priority
/kanban?lane=owner                # Swimlanes by owner
/kanban?lane=module               # Swimlanes by module
/kanban?status=!terminal          # Filter (same as list view)
```

## Open Questions

1. **Status column ordering** - What's the logical left-to-right flow? Current statuses in the database (by count):

   | Status           | Count | Category |
   | ---------------- | ----- | -------- |
   | Closed           | 813   | Terminal |
   | Rejected         | 77    | Terminal |
   | Ready for Retest | 70    | Active   |
   | Testing Complete | 67    | Active   |
   | Duplicate        | 53    | Terminal |
   | Open             | 41    | Active   |
   | In Development   | 40    | Active   |
   | New              | 38    | Active   |
   | Blocked          | 32    | Active   |
   | Deferred         | 22    | Terminal |
   | Reopen           | 7     | Active   |
   | Fixed            | 3     | Active   |

   Proposed default order:

   ```
   Blocked → New → Open → Reopen → In Development → Fixed → Ready for Retest → Testing Complete → Closed
   ```

   Blocked is first because these items need immediate attention and should be impossible to miss. The rest follow workflow progression left-to-right.

   Terminal statuses (Rejected, Duplicate, Deferred) hidden by default, shown with `?status=` filter or a toggle.

   Should this be configurable, or is a sensible default enough?

2. **Swimlane options** - Which fields make sense for swimlanes?
   - `priority` - Group by P1, P2, P3, P4
   - `owner` - Group by assignee
   - `module` - Group by module/area
   - `workstream` - Group by workstream
   - Others? Should we support arbitrary fields?

3. **Card content** - What to show on each card?
   - Proposal: ID, priority badge, truncated title, owner avatar/initials
   - Should we show age/staleness indicators?

4. **Column collapse** - Should users be able to collapse columns to focus on specific statuses?

## Implementation Details

### API Endpoint

New endpoint to fetch defects grouped for kanban display:

```
GET /api/kanban?lane=priority&status=!terminal
```

Response could either:

- (A) Return flat defect list, let frontend group them
- (B) Return pre-grouped structure

Option A is simpler and reuses existing code. The frontend already has the defect list; grouping is cheap in JS.

### Frontend Components

```
ui/src/routes/kanban/
├── +page.svelte          # Main kanban view
└── KanbanCard.svelte     # Individual defect card

ui/src/lib/components/
└── KanbanBoard.svelte    # Reusable board component (columns + swimlanes)
```

### Status Ordering

Add to `constants.py` (Python) and `lib/constants.ts` (frontend):

```python
# Kanban column order (Blocked first for visibility, then workflow progression)
STATUS_ORDER = [
    "Blocked",
    "New",
    "Open",
    "Reopen",
    "In Development",
    "Fixed",
    "Ready for Retest",
    "Testing Complete",
    "Closed",
]

# Terminal statuses (hidden by default on kanban)
# Note: TERMINAL_STATUSES already exists in constants.py
KANBAN_HIDDEN_STATUSES = ["Rejected", "Duplicate", "Deferred"]
```

### Keyboard Shortcuts

Extend existing keyboard handling:

| Key     | Action                                                                      |
| ------- | --------------------------------------------------------------------------- |
| `g b`   | Go to kanban board                                                          |
| `←/→`   | Move focus to top of previous/next column                                   |
| `↑/↓`   | Move focus between cards in column (wraps to adjacent column at boundaries) |
| `Enter` | Open focused card                                                           |
| `Esc`   | Clear focus                                                                 |

## Alternatives Considered

| Option                | Pros                   | Cons                                     | Why Not                                       |
| --------------------- | ---------------------- | ---------------------------------------- | --------------------------------------------- |
| Drag-and-drop editing | Full kanban experience | Requires ALM write access, complex       | Read-only is simpler, we don't have write API |
| CLI kanban view       | Works in terminal      | Limited space, poor UX for visual layout | Web UI is better suited for this              |

## Out of Scope

| Item                         | Rationale                                   |
| ---------------------------- | ------------------------------------------- |
| Drag-and-drop status changes | Would require ALM write API access          |
| WIP limits                   | Nice-to-have, but adds complexity           |
| Custom column ordering UI    | Start with sensible defaults, add if needed |
| Card color coding            | Could be future enhancement                 |

## Future Enhancements

1. **WIP limits** - Show warning when column exceeds configurable limit
2. **Card color by priority** - Visual priority indicators
3. **Cumulative flow diagram** - Track column sizes over time
4. **Collapsed columns** - Hide/minimize columns to focus on specific statuses
