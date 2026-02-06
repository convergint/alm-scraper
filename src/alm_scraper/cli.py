import json
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

from alm_scraper.api import ALMClient
from alm_scraper.config import Config, get_config_path, load_config, save_config
from alm_scraper.curl_parser import parse_curl
from alm_scraper.db import count_defects, get_db_path, get_defect_by_id, get_stats, list_defects
from alm_scraper.defect import parse_alm_response
from alm_scraper.display import (
    format_defect,
    format_defect_json,
    format_defect_markdown,
    format_defect_table,
    format_defects_json,
    format_defects_markdown,
    format_stats,
    format_stats_json,
)
from alm_scraper.query import execute_query, get_schema_help
from alm_scraper.storage import sync_defects

err = Console(stderr=True)

# Hardcoded ALM config - same for all team members
ALM_BASE_URL = "https://alm.deloitte.com/qcbin"
ALM_DOMAIN = "CONVERGINT"
ALM_PROJECT = "Convergint_Transformation"
ALM_COOKIE_DOMAIN = "alm.deloitte.com"
ALM_LOGIN_URL = (
    "https://alm.deloitte.com/qcbin/webrunner/"
    "#/domains/CONVERGINT/projects/Convergint_Transformation/defects"
)


def require_db() -> None:
    """Exit with error if database doesn't exist."""
    db_path = get_db_path()
    if not db_path.exists():
        err.print("[red]Error: No defects synced yet.[/red]")
        err.print()
        err.print("Run 'alm sync' or 'alm sync-file <file>' first.")
        sys.exit(1)


def _is_oauth_redirect(response: httpx.Response) -> bool:
    """Check if response is an OAuth redirect (session expired)."""
    if response.status_code not in (301, 302, 303, 307, 308):
        return False
    location = response.headers.get("location", "")
    return "oauth2" in location or "auth" in location


def _handle_http_error(e: httpx.HTTPStatusError) -> None:
    """Handle HTTP errors with helpful messages."""
    response = e.response

    if _is_oauth_redirect(response):
        err.print("[red]Error: Session expired - OAuth re-authentication required[/red]")
        err.print()
        err.print("Try auto-extracting cookies from your browser:")
        err.print("  [bold]alm config import-browser[/bold]")
        err.print("  [dim](first run will prompt for Keychain access)[/dim]")
        err.print()
        err.print("If that doesn't work, log into ALM first:")
        err.print(f"  {ALM_LOGIN_URL}")
    elif response.status_code in (401, 403):
        err.print(f"[red]Error: HTTP {response.status_code} - Authentication failed[/red]")
        err.print()
        err.print("Your session may have expired. To refresh:")
        err.print("  1. Log into ALM in your browser")
        err.print("  2. Copy a request as cURL from DevTools")
        err.print("  3. Run: [bold]alm config import-curl[/bold]")
    else:
        err.print(f"[red]Error: HTTP {response.status_code}[/red]")

    sys.exit(1)


@click.group()
@click.version_option()
def main() -> None:
    """CLI for scraping ALM defect data into searchable local files."""


@main.command()
@click.argument("defect_id", type=int)
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["rich", "markdown", "md", "json"]),
    default="rich",
    help="Output format (default: rich)",
)
def show(defect_id: int, output_format: str) -> None:
    """Show details for a specific defect by ID."""
    require_db()

    defect = get_defect_by_id(defect_id)

    if defect is None:
        err.print(f"[red]Error: Defect #{defect_id} not found[/red]")
        sys.exit(1)
        return  # help type checker

    if output_format == "rich":
        out = Console()
        format_defect(defect, out)
    elif output_format in ("markdown", "md"):
        print(format_defect_markdown(defect))
    elif output_format == "json":
        print(format_defect_json(defect))


@main.command("list")
@click.option("-s", "--status", multiple=True, help="Filter by status (can repeat)")
@click.option("-o", "--owner", multiple=True, help="Filter by owner (can repeat)")
@click.option("-m", "--module", multiple=True, help="Filter by module (can repeat)")
@click.option("-t", "--type", "defect_type", multiple=True, help="Filter by type (can repeat)")
@click.option("-p", "--priority", multiple=True, help="Filter by priority (can repeat)")
@click.option("-w", "--workstream", multiple=True, help="Filter by workstream (can repeat)")
@click.option("-n", "--limit", default=50, help="Maximum results [default: 50]")
@click.option("--all", "show_all", is_flag=True, help="Show all results (no limit)")
@click.option(
    "-f",
    "--format",
    "output_format",
    type=click.Choice(["table", "markdown", "md", "json"]),
    default="table",
    help="Output format [default: table]",
)
def list_cmd(
    status: tuple[str, ...],
    owner: tuple[str, ...],
    module: tuple[str, ...],
    defect_type: tuple[str, ...],
    priority: tuple[str, ...],
    workstream: tuple[str, ...],
    limit: int,
    show_all: bool,
    output_format: str,
) -> None:
    """List defects with optional filtering.

    By default, only open defects are shown. Use --status to override.
    """
    require_db()

    effective_limit = None if show_all else limit

    # Default to open defects if no status filter provided
    effective_status = status if status else ("open",)

    defects = list_defects(
        status=effective_status,
        owner=owner,
        module=module,
        defect_type=defect_type,
        priority=priority,
        workstream=workstream,
        limit=effective_limit,
    )

    total = count_defects()

    if output_format == "table":
        out = Console()
        format_defect_table(defects, out, total_count=total)
    elif output_format in ("markdown", "md"):
        print(format_defects_markdown(defects))
    elif output_format == "json":
        print(format_defects_json(defects))


@main.command()
@click.option("--all", "include_closed", is_flag=True, help="Include closed defects in breakdowns")
@click.option("--top", "top_n", default=5, help="Number of items in each breakdown [default: 5]")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def stats(include_closed: bool, top_n: int, as_json: bool) -> None:
    """Show aggregate statistics about defects."""
    require_db()

    stats_data = get_stats(include_closed=include_closed, top_n=top_n)

    if stats_data is None:
        err.print("[red]Error: Could not load stats.[/red]")
        sys.exit(1)
        return  # help type checker

    if as_json:
        print(format_stats_json(stats_data))
    else:
        out = Console()
        format_stats(stats_data, out, include_closed=include_closed, top_n=top_n)


class QueryHelpCommand(click.Command):
    """Custom command that shows schema in --help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Override to append schema documentation to help."""
        super().format_help(ctx, formatter)
        formatter.write("\n")
        formatter.write(get_schema_help())


@main.command(cls=QueryHelpCommand)
@click.argument("sql", required=False)
@click.option("--csv", "as_csv", is_flag=True, help="Output as CSV")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def query(sql: str | None, as_csv: bool, as_json: bool) -> None:
    """Execute a SQL query against the defects database.

    SQL can be passed as an argument or piped via stdin.
    """
    import sqlite3

    # Read from stdin if no argument provided
    if sql is None:
        if sys.stdin.isatty():
            err.print("[red]Error: No SQL provided.[/red]")
            err.print()
            err.print('Usage: alm query "SELECT ..."')
            err.print('   or: echo "SELECT ..." | alm query')
            sys.exit(1)
        sql = sys.stdin.read().strip()
        if not sql:
            err.print("[red]Error: No SQL provided.[/red]")
            sys.exit(1)

    try:
        result = execute_query(sql)
    except FileNotFoundError:
        err.print("[red]Error: No defects synced yet.[/red]")
        err.print()
        err.print("Run 'alm sync' or 'alm sync-file <file>' first.")
        sys.exit(1)
    except ValueError as e:
        err.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except sqlite3.Error as e:
        err.print(f"[red]SQL Error: {e}[/red]")
        sys.exit(1)

    if as_json:
        print(result.to_json())
    elif as_csv:
        print(result.to_csv())
    else:
        print(result.to_table())


@main.command()
@click.option("--debug", is_flag=True, help="Print request/response debug info")
def sync(debug: bool) -> None:
    """Sync defects from ALM to local storage."""
    config = load_config()

    if config is None:
        err.print("[red]Error: No configuration found.[/red]")
        err.print()
        err.print("Log into ALM in your browser, then run:")
        err.print("  [bold]alm config import-browser[/bold]")
        err.print("  [dim](first run will prompt for Keychain access)[/dim]")
        err.print()
        err.print("If that doesn't work, log into ALM first:")
        err.print(f"  {ALM_LOGIN_URL}")
        sys.exit(1)
        return  # help type checker

    err.print(f"Fetching defects from {config.base_url}...")

    client = ALMClient(config, debug=debug)

    def on_page(page: int, total: int, count: int) -> None:
        err.print(f"  Page {page}/{total}: {count} defects")

    try:
        data = client.fetch_all_defects(on_page=on_page)
    except httpx.HTTPStatusError as e:
        _handle_http_error(e)
    except httpx.RequestError as e:
        err.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    err.print("Parsing defects...")
    defects = parse_alm_response(data)

    err.print("Syncing to local storage...")
    result = sync_defects(defects)

    err.print()
    err.print(f"[green]Synced {result.defect_count} defects[/green]")
    err.print(f"  {result.data_dir / result.history_base}.json")
    err.print(f"  {result.data_dir / result.history_base}.db")


@main.command("sync-file")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def sync_file(file: Path) -> None:
    """Import defects from a local ALM JSON export file.

    This is useful for testing the sync pipeline without hitting the network.
    The file should be a raw ALM API response with an 'entities' array.
    """
    err.print(f"Reading {file}...")

    with file.open() as f:
        data = json.load(f)

    err.print("Parsing defects...")
    defects = parse_alm_response(data)
    err.print(f"  Found {len(defects)} defects")

    err.print("Syncing to local storage...")
    result = sync_defects(defects)

    err.print()
    err.print(f"[green]Synced {result.defect_count} defects[/green]")
    err.print(f"  {result.data_dir / result.history_base}.json")
    err.print(f"  {result.data_dir / result.history_base}.db")


@main.group()
def config() -> None:
    """Manage configuration."""


@config.command("import-curl")
def import_curl() -> None:
    """Import configuration from a curl command.

    Copy a curl command from browser DevTools (Network tab -> right-click -> Copy as cURL)
    and paste it here. The command should be for an ALM REST API request.

    Can also be piped: pbpaste | alm config import-curl
    """
    if sys.stdin.isatty():
        # Interactive mode - prompt for input
        err.print("Paste curl command (press Enter twice when done):")
        err.print()

        lines: list[str] = []
        empty_count = 0

        while empty_count < 1:
            try:
                line = input()
                if not line:
                    empty_count += 1
                else:
                    empty_count = 0
                    lines.append(line)
            except EOFError:
                break

        if not lines:
            err.print("[red]Error: No input provided[/red]")
            sys.exit(1)

        curl_command = "\n".join(lines)
    else:
        # Piped input - read all at once
        curl_command = sys.stdin.read().strip()

        if not curl_command:
            err.print("[red]Error: No input provided[/red]")
            sys.exit(1)

    try:
        parsed = parse_curl(curl_command)
    except ValueError as e:
        err.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    config_obj = Config(
        base_url=parsed.base_url,
        domain=parsed.domain,
        project=parsed.project,
        cookies=parsed.cookies,
    )

    path = save_config(config_obj)

    err.print()
    err.print("[green]Imported config:[/green]")
    err.print(f"  base_url: {config_obj.base_url}")
    err.print(f"  domain:   {config_obj.domain}")
    err.print(f"  project:  {config_obj.project}")
    err.print(f"  cookies:  {len(config_obj.cookies)} cookies extracted")
    err.print()
    err.print(f"[green]Saved to {path}[/green]")


@config.command("import-browser")
@click.option(
    "--browser",
    type=click.Choice(["arc", "brave", "chrome", "edge", "firefox"]),
    help="Force a specific browser",
)
def import_browser(browser: str | None) -> None:
    """Import cookies from your browser's cookie store.

    Searches Arc, Brave, Chrome, Edge, and Firefox for ALM cookies.
    Uses the first browser that has valid cookies.
    """
    from alm_scraper.browser import extract_cookies

    err.print("Searching for ALM cookies...")
    err.print("[dim]Note: First run may prompt for Keychain access.[/dim]")
    err.print()

    def on_status(name: str, status: str) -> None:
        err.print(f"  {name}: {status}")

    try:
        browser_name, cookies = extract_cookies(
            ALM_COOKIE_DOMAIN, browser=browser, on_status=on_status
        )
    except RuntimeError as e:
        err.print()
        err.print(f"[red]Error: {e}[/red]")
        err.print()
        err.print("Log into ALM in Arc, Brave, Chrome, Edge, or Firefox:")
        err.print(f"  {ALM_LOGIN_URL}")
        err.print()
        err.print("Then run 'alm config import-browser' again.")
        sys.exit(1)

    new_config = Config(
        base_url=ALM_BASE_URL,
        domain=ALM_DOMAIN,
        project=ALM_PROJECT,
        cookies=cookies,
    )

    path = save_config(new_config)

    err.print()
    err.print(f"[green]Imported {len(cookies)} cookies from {browser_name}[/green]")
    err.print(f"  base_url: {new_config.base_url}")
    err.print(f"  domain:   {new_config.domain}")
    err.print(f"  project:  {new_config.project}")
    err.print()
    err.print(f"[green]Saved to {path}[/green]")


@config.command("show")
def config_show() -> None:
    """Show current configuration."""
    path = get_config_path()

    if not path.exists():
        err.print(f"[yellow]No config file found at {path}[/yellow]")
        err.print()
        err.print("Run 'alm config import-curl' to create one.")
        sys.exit(1)

    with path.open() as f:
        err.print(f.read())


@config.command("path")
def config_path() -> None:
    """Show path to configuration file."""
    print(get_config_path())


@main.command()
@click.option("--port", default=8753, help="Port to run on")
@click.option("--no-open", is_flag=True, help="Don't open browser automatically")
@click.option("--reload", is_flag=True, help="Auto-reload when UI files change")
def ui(port: int, no_open: bool, reload: bool) -> None:
    """Launch local web UI for browsing defects."""
    require_db()

    import threading
    import time
    import webbrowser

    import uvicorn

    url = f"http://localhost:{port}"

    # Open browser after a short delay (give server time to start)
    if not no_open:

        def open_browser() -> None:
            time.sleep(1)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    err.print(f"Starting ALM UI at {url}")
    if reload:
        err.print("[dim]Watching for changes (rebuild UI with 'make build-ui')[/dim]")
    err.print("Press Ctrl+C to stop")
    err.print()

    # Get paths for reload watching
    reload_dirs: list[str] = []
    if reload:
        from alm_scraper.ui import api

        static_dir = Path(api.__file__).parent / "static"
        if static_dir.exists():
            reload_dirs.append(str(static_dir))
        # Also watch the api module itself
        reload_dirs.append(str(Path(api.__file__).parent))

    uvicorn.run(
        "alm_scraper.ui.api:app",
        host="127.0.0.1",
        port=port,
        log_level="warning" if not reload else "info",
        reload=reload,
        reload_dirs=reload_dirs if reload_dirs else None,
    )


if __name__ == "__main__":
    main()
