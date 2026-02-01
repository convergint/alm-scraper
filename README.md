# alm-scraper

A CLI tool for scraping defect data from ALM (Application Lifecycle Manager) and providing a local, fast interface for searching and browsing.

## Why?

The ALM website is painfully slow and you can't link directly to defects. This tool:

- Syncs defect data to a local SQLite database
- Provides fast CLI access to search and view defects
- Includes a local web UI that doesn't suck

## Installation

```bash
# Clone and install
git clone <repo>
cd alm-scraper
make install
```

This installs the `alm` command to `~/.local/bin/alm`.

## Quick Start

```bash
# First time: import cookies from your browser
# (must be logged into ALM in Arc, Chrome, Edge, or Firefox)
alm config import-browser

# Sync defects from ALM
alm sync

# Launch the web UI
alm ui

# Or use the CLI
alm show 993              # View a specific defect
alm list                  # List open defects
alm list -s closed        # List closed defects
alm stats                 # Show aggregate statistics
alm query "SELECT ..."    # Run raw SQL queries
```

## Commands

### `alm sync`

Fetch defects from ALM and store locally.

```bash
alm sync           # Sync from ALM (requires valid session)
alm sync --debug   # Show request/response details
```

### `alm ui`

Launch a local web interface for browsing defects.

```bash
alm ui              # Start server and open browser
alm ui --port 9000  # Use a different port
alm ui --no-open    # Don't open browser automatically
```

### `alm show <id>`

View a single defect.

```bash
alm show 993              # Rich terminal output
alm show 993 -f markdown  # Markdown format
alm show 993 -f json      # JSON format
```

### `alm list`

List defects with filtering.

```bash
alm list                        # Open defects (default)
alm list -s closed              # Closed defects
alm list -p P1                  # P1 priority only
alm list -o jsmith              # By owner
alm list -m "Data Migration"    # By module
alm list --all                  # No limit
alm list -f json                # JSON output
```

### `alm stats`

Show aggregate statistics.

```bash
alm stats           # Open defects only
alm stats --all     # Include closed
alm stats --json    # JSON output
```

### `alm query`

Run raw SQL queries against the defects database.

```bash
alm query "SELECT id, name FROM defects WHERE priority = 'P1-Critical'"
alm query --help    # Show schema documentation
```

### `alm config`

Manage authentication.

```bash
alm config import-browser    # Extract cookies from browser
alm config import-curl       # Import from cURL command
alm config show              # Show current config
alm config path              # Show config file path
```

## Authentication

ALM uses Microsoft 365 SSO, so we extract session cookies from your browser.

1. Log into ALM in your browser: https://alm.deloitte.com/qcbin/webrunner/#/domains/CONVERGINT/projects/Convergint_Transformation/defects
2. Run `alm config import-browser`
3. First run will prompt for Keychain access (to decrypt browser cookies)

Supported browsers: Arc, Chrome, Edge, Firefox (Safari requires Full Disk Access).

When your session expires, just run `alm config import-browser` again.

## Development

### Prerequisites

- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Node.js 18+ (for UI development)

### Commands

```bash
make check      # Run lint, typecheck, and tests
make format     # Format code with ruff
make test       # Run pytest
make lint       # Run ruff check
make typecheck  # Run ty check

make build-ui   # Build SvelteKit and copy to static/
make dev-ui     # Run SvelteKit dev server on :5173
```

### UI Development

For frontend work, run both servers:

```bash
# Terminal 1: Backend API
alm ui --no-open  # Runs on :8753

# Terminal 2: Frontend dev server with hot reload
make dev-ui       # Runs on :5173, proxies API to :8753
```

After making UI changes, rebuild for distribution:

```bash
make build-ui     # Builds to src/alm_scraper/ui/static/
```

### Project Structure

```
src/alm_scraper/
├── cli.py          # CLI entry point (typer)
├── api.py          # ALM REST client
├── db.py           # SQLite database queries
├── constants.py    # Shared business constants (TERMINAL_STATUSES, etc.)
├── sql_helpers.py  # SQL query builders
├── defect.py       # Defect dataclass model
├── browser.py      # Cookie extraction from browsers
├── ui/
│   ├── api.py      # FastAPI backend for web UI
│   └── static/     # Built SvelteKit app (generated)
└── ...

ui/                 # SvelteKit frontend source
├── src/
│   ├── routes/
│   │   ├── +page.svelte           # Defect list with search/filters
│   │   ├── stats/+page.svelte     # Dashboard with charts
│   │   └── defects/[id]/          # Defect detail view
│   └── lib/
│       ├── api.ts                 # API client functions
│       ├── types.ts               # TypeScript interfaces
│       └── components/
│           ├── KeyboardShortcuts.svelte  # Vim-style shortcuts
│           ├── BurndownChart.svelte      # Chart.js burndown
│           └── ...
└── ...

tests/
├── test_api.py         # FastAPI endpoint tests
├── test_sql_helpers.py # SQL builder unit tests
└── ...

rfcs/                   # Design documents
└── 009-keyboard-shortcuts.md
```

### Key Patterns

**Status Filters**: The UI supports special status values:

- `!terminal` - Excludes closed, rejected, duplicate, deferred
- `!closed` - Excludes only closed

**Keyboard Shortcuts**: Vim-style navigation in the web UI:

- `j/k` - Navigate list, `Enter` - Open defect
- `g d` - Go to defect by ID, `g h` - Home, `g s` - Stats
- `/` - Focus search, `?` - Help overlay

**Svelte 5**: The UI uses Svelte 5 with runes (`$state`, `$effect`, `$derived`, `$props`)

## Data Storage

- Config: `~/.config/alm-scraper/config.json`
- Database: `~/.local/share/alm-scraper/defects.db`
- History: `~/.local/share/alm-scraper/history/`
