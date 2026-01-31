import json
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console

from alm_scraper.api import ALMClient
from alm_scraper.config import Config, get_config_path, load_config, save_config
from alm_scraper.curl_parser import parse_curl
from alm_scraper.db import count_defects, get_db_path, get_defect_by_id, list_defects
from alm_scraper.defect import parse_alm_response
from alm_scraper.display import (
    format_defect,
    format_defect_json,
    format_defect_markdown,
    format_defect_table,
    format_defects_json,
    format_defects_markdown,
)
from alm_scraper.storage import sync_defects

err = Console(stderr=True)


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
    db_path = get_db_path()

    if not db_path.exists():
        err.print("[red]Error: No defects synced yet.[/red]")
        err.print()
        err.print("Run 'alm sync' or 'alm sync-file <file>' first.")
        sys.exit(1)

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
    db_path = get_db_path()

    if not db_path.exists():
        err.print("[red]Error: No defects synced yet.[/red]")
        err.print()
        err.print("Run 'alm sync' or 'alm sync-file <file>' first.")
        sys.exit(1)

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
def sync() -> None:
    """Sync defects from ALM to local storage."""
    config = load_config()

    if config is None:
        err.print("[red]Error: No configuration found.[/red]")
        err.print()
        err.print("Run 'alm config import-curl' first to set up authentication.")
        sys.exit(1)
        return  # help type checker

    err.print(f"Fetching defects from {config.base_url}...")

    client = ALMClient(config)

    def on_page(page: int, total: int, count: int) -> None:
        err.print(f"  Page {page}/{total}: {count} defects")

    try:
        data = client.fetch_all_defects(on_page=on_page)
    except httpx.HTTPStatusError as e:
        err.print(f"[red]Error: HTTP {e.response.status_code}[/red]")
        if e.response.status_code in (401, 403):
            err.print()
            err.print("Your session may have expired. To refresh:")
            err.print("1. Log into ALM in your browser")
            err.print("2. Copy a request as cURL from DevTools")
            err.print("3. Run: alm config import-curl")
        sys.exit(1)
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


if __name__ == "__main__":
    main()
