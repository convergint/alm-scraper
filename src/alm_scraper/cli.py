import sys

import click
from rich.console import Console

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


if __name__ == "__main__":
    main()
