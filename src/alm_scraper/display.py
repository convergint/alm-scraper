"""Display formatting for defects."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from alm_scraper.defect import Defect


def format_defect(defect: Defect, console: Console) -> None:
    """Display a defect nicely formatted to the console.

    Args:
        defect: The defect to display.
        console: Rich console to write to.
    """
    # Header with ID and name
    title = f"Defect #{defect.id}: {defect.name}"

    # Status line with color coding
    status_color = _get_status_color(defect.status)
    priority_color = _get_priority_color(defect.priority)

    status_line = Text()
    status_line.append("Status: ")
    status_line.append(defect.status or "Unknown", style=status_color)
    status_line.append(" | Priority: ")
    status_line.append(defect.priority or "Unknown", style=priority_color)
    if defect.severity and defect.severity != defect.priority:
        status_line.append(" | Severity: ")
        status_line.append(defect.severity)

    # Metadata table
    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="dim")
    meta.add_column()

    meta.add_row("Owner:", defect.owner or "-")
    meta.add_row("Detected by:", defect.detected_by or "-")
    meta.add_row("Created:", defect.created or "-")
    meta.add_row("Modified:", defect.modified or "-")
    if defect.closed:
        meta.add_row("Closed:", defect.closed)

    if defect.application or defect.workstream or defect.module:
        meta.add_row("", "")  # spacer
        if defect.application:
            meta.add_row("Application:", defect.application)
        if defect.workstream:
            meta.add_row("Workstream:", defect.workstream)
        if defect.module:
            meta.add_row("Module:", defect.module)

    if defect.defect_type:
        meta.add_row("Type:", defect.defect_type)

    # Print everything
    console.print()
    console.print(Panel(title, style="bold"))
    console.print(status_line)
    console.print()
    console.print(meta)

    # Description
    if defect.description:
        console.print()
        console.print("[bold]Description:[/bold]")
        console.print(defect.description)

    # Dev comments
    if defect.dev_comments:
        console.print()
        console.print("[bold]Dev Comments:[/bold]")
        console.print(defect.dev_comments)

    console.print()


def _get_status_color(status: str | None) -> str:
    """Get color for status display."""
    if not status:
        return "white"

    status_lower = status.lower()
    if status_lower == "closed":
        return "green"
    if status_lower == "open":
        return "red"
    if "progress" in status_lower:
        return "yellow"
    return "white"


def _get_priority_color(priority: str | None) -> str:
    """Get color for priority display."""
    if not priority:
        return "white"

    priority_lower = priority.lower()
    if "critical" in priority_lower or "p1" in priority_lower:
        return "red bold"
    if "high" in priority_lower or "p2" in priority_lower:
        return "yellow"
    if "medium" in priority_lower or "p3" in priority_lower:
        return "white"
    if "low" in priority_lower or "p4" in priority_lower:
        return "dim"
    return "white"
