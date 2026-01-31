import sys

import click
from rich.console import Console

from alm_scraper.config import Config, get_config_path, save_config
from alm_scraper.curl_parser import parse_curl

err = Console(stderr=True)


@click.group()
@click.version_option()
def main() -> None:
    """CLI for scraping ALM defect data into searchable local files."""


@main.command()
@click.argument("defect_id", type=int)
def show(defect_id: int) -> None:
    """Show details for a specific defect by ID."""
    err.print(f"[yellow]show defect {defect_id} - not yet implemented[/yellow]")
    sys.exit(1)


@main.command()
def sync() -> None:
    """Sync defects from ALM to local storage."""
    err.print("[yellow]sync - not yet implemented[/yellow]")
    sys.exit(1)


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
