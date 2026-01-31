# RFC 008: Local Web UI

**Status:** Draft  
**Author:** Claude  
**Created:** 2026-01-31

---

## Summary

Add `alm ui` command that launches a local web server with a clean, fast interface for browsing and searching defects. No more suffering through the slow, clunky ALM website.

## Problem

The ALM website is dogshit:

- Slow to load and navigate
- Clunky UI that requires too many clicks
- Search is painful
- Can't easily see defect details without multiple page loads

We already have all the data locally in SQLite. Let's put a nice UI on it.

## Proposed Solution

A local web server (FastAPI + HTMX) that provides:

- Fast defect list with filtering and search
- Clean defect detail view
- Full-text search across all fields
- Keyboard navigation

### User Experience

```bash
$ alm ui
Starting ALM UI at http://localhost:8753
Opening browser...
```

Browser opens to a clean interface showing:

- Search bar at top
- Filter dropdowns (status, priority, owner, module, etc.)
- Sortable defect table
- Click a defect to see full details

### Tech Stack

- **SvelteKit** - Fast, modern frontend framework with great DX
- **FastAPI** - Python API backend
- **Tailwind CSS** - Clean styling
- **TypeScript** - Type safety in frontend

Why this stack:

- SvelteKit provides rich interactivity and fast navigation
- Separate dev servers for hot reload during development
- Built static output embedded in Python package for distribution
- End users just run `alm ui` - no Node required

### Routes

**Frontend (SvelteKit):**
| Route | Description |
|-------|-------------|
| `/` | Defect list with filters |
| `/defects/[id]` | Defect detail page |

**API (FastAPI):**
| Route | Description |
|-------|-------------|
| `GET /api/defects` | List defects with filters, pagination |
| `GET /api/defects/{id}` | Single defect details |
| `GET /api/search?q=...` | Full-text search |
| `GET /api/stats` | Aggregate statistics |

### Features

**List View:**

- Default: open defects, sorted by priority then age
- Filter by: status, priority, owner, module, type, workstream
- Sort by: priority, created, modified, ID
- Pagination or infinite scroll
- Click row to view details

**Detail View:**

- All defect fields displayed cleanly
- Description and dev_comments rendered as HTML
- Back button / keyboard nav (Escape)
- Link to next/prev defect

**Search:**

- Full-text search using FTS5
- Search as you type (debounced)
- Highlights matching terms

### Commands

```bash
$ alm ui --help
Usage: alm ui [OPTIONS]

  Launch local web UI for browsing defects.

Options:
  --port INTEGER  Port to run on [default: 8753]
  --no-open       Don't open browser automatically
  --help          Show this message and exit.
```

## Error Handling

| Scenario          | What User Sees                                         | Recovery           |
| ----------------- | ------------------------------------------------------ | ------------------ |
| No defects synced | Error page: "No defects synced. Run 'alm sync' first." | Run sync           |
| Port in use       | "Error: Port 8753 in use. Try --port 8754"             | Use different port |
| Defect not found  | 404 page with link back to list                        | Click link         |

## Implementation Details

### Dependencies

**Python (pyproject.toml):**

```toml
dependencies = [
    ...
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
]
```

**Frontend (ui/package.json):**

- SvelteKit
- Tailwind CSS
- TypeScript

### File Structure

```
ui/                              # SvelteKit project
├── src/
│   ├── routes/
│   │   ├── +page.svelte         # Defect list
│   │   └── defects/
│   │       └── [id]/
│   │           └── +page.svelte # Defect detail
│   ├── lib/
│   │   ├── api.ts               # API client
│   │   └── components/          # Reusable components
│   └── app.html
├── package.json
├── svelte.config.js
├── tailwind.config.js
└── vite.config.ts

src/alm_scraper/
├── ui/
│   ├── __init__.py
│   ├── api.py                   # FastAPI app with API routes
│   └── static/                  # Built SvelteKit output
└── cli.py                       # Add 'ui' command
```

### Key Components

**FastAPI Backend:**

```python
# src/alm_scraper/ui/api.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from alm_scraper.db import list_defects, get_defect_by_id

app = FastAPI(title="ALM Defects API")

@app.get("/api/defects")
async def get_defects(status: str = "open", page: int = 1, limit: int = 50):
    defects = list_defects(status=(status,), limit=limit, ...)
    return {"defects": [d.model_dump() for d in defects], "page": page}

@app.get("/api/defects/{defect_id}")
async def get_defect(defect_id: int):
    defect = get_defect_by_id(defect_id)
    return defect.model_dump() if defect else None

# Serve static SvelteKit build
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

**CLI Command:**

```python
# src/alm_scraper/cli.py
@main.command()
@click.option("--port", default=8753, help="Port to run on")
@click.option("--no-open", is_flag=True, help="Don't open browser")
def ui(port: int, no_open: bool) -> None:
    """Launch local web UI for browsing defects."""
    require_db()

    import uvicorn
    import webbrowser

    if not no_open:
        webbrowser.open(f"http://localhost:{port}")

    uvicorn.run("alm_scraper.ui.api:app", host="127.0.0.1", port=port)
```

**Development Workflow:**

```bash
# Terminal 1: Run FastAPI backend
alm ui --no-open

# Terminal 2: Run SvelteKit dev server (proxies /api to FastAPI)
cd ui && npm run dev
```

**Build for Distribution:**

```bash
make build-ui  # Builds SvelteKit and copies to src/alm_scraper/ui/static/
```

## Testing Strategy

### Manual Testing Checklist

- [ ] `alm ui` starts server and opens browser
- [ ] Defect list loads with default filters
- [ ] Filters work (status, priority, owner, etc.)
- [ ] Sorting works
- [ ] Search returns results
- [ ] Defect detail page shows all fields
- [ ] HTML content renders correctly (description, dev_comments)
- [ ] Keyboard navigation works
- [ ] Error states display correctly

## Decisions

1. **SvelteKit + FastAPI** - Rich frontend with Python API backend. Separate dev servers, embedded build for distribution.
2. **Pagination** - 50 defects per page with prev/next buttons. Simpler than infinite scroll.
3. **Dark mode only** - Default and only theme for v1. No toggle needed.
4. **Tailwind CSS** - Utility classes are predictable and easy to maintain/modify programmatically.

## Out of Scope

| Item                | Rationale                    |
| ------------------- | ---------------------------- |
| Editing defects     | Read-only view of local data |
| Real-time sync      | Manual sync is fine          |
| User authentication | Local tool, no auth needed   |
| Mobile optimization | Desktop-focused for now      |

## Future Enhancements

1. **Keyboard shortcuts** - j/k navigation, / to search
2. **Dark mode toggle**
3. **Saved filters / views**
4. **Export to CSV/JSON**
5. **Side-by-side defect comparison**
