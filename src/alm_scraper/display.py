"""Display formatting for defects."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from alm_scraper.db import Stats
from alm_scraper.defect import Defect, strip_html_preserve_structure


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

    # Dev comments - parse from HTML for proper formatting
    dev_comments = strip_html_preserve_structure(defect.dev_comments_html)
    if dev_comments:
        console.print()
        console.print("[bold]Dev Comments:[/bold]")
        console.print(dev_comments)

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


def format_defect_markdown(defect: Defect) -> str:
    """Format a defect as markdown.

    Args:
        defect: The defect to format.

    Returns:
        Markdown string.
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Defect #{defect.id}: {defect.name}")
    lines.append("")

    # Status line
    status_parts = [f"**Status:** {defect.status or 'Unknown'}"]
    status_parts.append(f"**Priority:** {defect.priority or 'Unknown'}")
    if defect.owner:
        status_parts.append(f"**Owner:** {defect.owner}")
    lines.append(" | ".join(status_parts))
    lines.append("")

    # Metadata table
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")

    if defect.detected_by:
        lines.append(f"| Detected by | {defect.detected_by} |")
    if defect.created:
        lines.append(f"| Created | {defect.created} |")
    if defect.modified:
        lines.append(f"| Modified | {defect.modified} |")
    if defect.closed:
        lines.append(f"| Closed | {defect.closed} |")
    if defect.application:
        lines.append(f"| Application | {defect.application} |")
    if defect.workstream:
        lines.append(f"| Workstream | {defect.workstream} |")
    if defect.module:
        lines.append(f"| Module | {defect.module} |")
    if defect.defect_type:
        lines.append(f"| Type | {defect.defect_type} |")

    lines.append("")

    # Description
    if defect.description:
        lines.append("## Description")
        lines.append("")
        lines.append(defect.description)
        lines.append("")

    # Dev comments - parse from HTML for proper formatting
    dev_comments = strip_html_preserve_structure(defect.dev_comments_html)
    if dev_comments:
        lines.append("## Dev Comments")
        lines.append("")
        lines.append(dev_comments)
        lines.append("")

    return "\n".join(lines)


def format_defect_json(defect: Defect) -> str:
    """Format a defect as JSON.

    Args:
        defect: The defect to format.

    Returns:
        JSON string.
    """
    import json

    return json.dumps(defect.model_dump(), indent=2)


def format_defect_table(
    defects: list[Defect],
    console: Console,
    total_count: int | None = None,
) -> None:
    """Display defects in a compact table format.

    Args:
        defects: List of defects to display.
        console: Rich console to write to.
        total_count: Total number of defects (for "showing X of Y" message).
    """
    if not defects:
        console.print("[dim]No defects found[/dim]")
        return

    table = Table(box=None, padding=(0, 2), collapse_padding=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Pri", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("Owner", style="dim", no_wrap=True)

    for d in defects:
        status_style = _get_status_color(d.status)
        priority_style = _get_priority_color(d.priority)

        # Truncate name to fit
        name = d.name or ""
        if len(name) > 45:
            name = name[:42] + "..."

        # Short priority (P1, P2, P3, P4)
        pri = d.priority or "-"
        if pri.startswith("P") and "-" in pri:
            pri = pri.split("-")[0]

        # Truncate owner (remove domain suffix if present)
        owner = d.owner or "-"
        if "_" in owner:
            owner = owner.split("_")[0]
        if len(owner) > 15:
            owner = owner[:12] + "..."

        table.add_row(
            f"#{d.id}",
            Text(d.status or "-", style=status_style),
            Text(pri, style=priority_style),
            name,
            owner,
        )

    console.print(table)

    # Show count summary
    if total_count is not None and total_count > len(defects):
        console.print()
        console.print(f"[dim]Showing {len(defects)} of {total_count} defects[/dim]")
    else:
        console.print()
        console.print(f"[dim]{len(defects)} defects[/dim]")


def format_defects_json(defects: list[Defect]) -> str:
    """Format a list of defects as JSON.

    Args:
        defects: List of defects to format.

    Returns:
        JSON string.
    """
    import json

    return json.dumps([d.model_dump() for d in defects], indent=2)


def _format_days(days: float) -> str:
    """Format a duration in days as a human-readable string."""
    if days < 1:
        hours = int(days * 24)
        return f"{hours}h"
    elif days < 7:
        return f"{days:.0f}d"
    elif days < 30:
        weeks = days / 7
        return f"{weeks:.1f}w"
    else:
        months = days / 30
        return f"{months:.1f}mo"


def format_defects_markdown(defects: list[Defect]) -> str:
    """Format a list of defects as a markdown table.

    Args:
        defects: List of defects to format.

    Returns:
        Markdown string.
    """
    lines = [
        "| ID | Status | Priority | Name | Owner |",
        "|---:|--------|----------|------|-------|",
    ]

    for d in defects:
        name = d.name or ""
        if len(name) > 50:
            name = name[:47] + "..."
        owner = d.owner or "-"
        if "_" in owner:
            owner = owner.split("_")[0]

        lines.append(f"| #{d.id} | {d.status or '-'} | {d.priority or '-'} | {name} | {owner} |")

    return "\n".join(lines)


def format_stats(
    stats: Stats, console: Console, include_closed: bool = False, top_n: int = 5
) -> None:
    """Display aggregate statistics.

    Args:
        stats: Stats object with aggregate data.
        console: Rich console to write to.
        include_closed: Whether closed defects are included in breakdowns.
    """
    # Header
    console.print()
    console.print(
        f"Defects: [green]{stats.open_count} open[/green] / "
        f"[dim]{stats.closed_count} closed[/dim] ({stats.total} total)"
    )

    # Oldest open defect
    if stats.oldest_open:
        name = stats.oldest_open.name or ""
        if len(name) > 45:
            name = name[:42] + "..."
        console.print(
            f"Oldest open: [cyan]#{stats.oldest_open.id}[/cyan] "
            f"({stats.oldest_open.created}) - {name}"
        )

    # Close time stats
    if stats.close_time:
        console.print(
            f"Close time:  p50: [bold]{_format_days(stats.close_time.p50)}[/bold] | "
            f"p75: {_format_days(stats.close_time.p75)} | "
            f"avg: {_format_days(stats.close_time.avg)}"
        )

    # Determine the base count for percentages
    base_count = stats.total if include_closed else stats.open_count
    scope = "all" if include_closed else "open"

    def print_breakdown(
        title: str,
        items: list[tuple[str, int]],
        top_n: int | None = None,
        strip_domain: bool = False,
    ) -> None:
        if not items:
            return

        # Only show "top N" if we actually limited results
        top_label = f", top {len(items)}" if top_n and len(items) >= top_n else ""
        console.print()
        console.print(f"[bold]By {title}[/bold] ({scope}{top_label}):")

        # Process labels (optionally strip domain suffix)
        processed_items = []
        for label, count in items:
            if strip_domain and "_" in label:
                label = label.split("_")[0]
            processed_items.append((label, count))

        # Find max label width for alignment
        max_label = max(len(label) for label, _ in processed_items)
        max_count = max(count for _, count in processed_items)
        count_width = len(str(max_count))

        for label, count in processed_items:
            pct = (count / base_count * 100) if base_count > 0 else 0
            console.print(
                f"  {label:<{max_label}}  {count:>{count_width}}  [dim]({pct:.0f}%)[/dim]"
            )

    print_breakdown("Priority", stats.by_priority)
    print_breakdown("Module", stats.by_module, top_n=top_n)
    print_breakdown("Owner", stats.by_owner, top_n=top_n, strip_domain=True)
    print_breakdown("Type", stats.by_type, top_n=top_n)
    print_breakdown("Workstream", stats.by_workstream, top_n=top_n)

    console.print()


def format_stats_json(stats: Stats) -> str:
    """Format stats as JSON.

    Args:
        stats: Stats object with aggregate data.

    Returns:
        JSON string.
    """
    import json

    data: dict[str, object] = {
        "total": stats.total,
        "open": stats.open_count,
        "closed": stats.closed_count,
        "oldest_open": None,
        "close_time": None,
        "by_priority": dict(stats.by_priority),
        "by_module": dict(stats.by_module),
        "by_owner": dict(stats.by_owner),
        "by_type": dict(stats.by_type),
        "by_workstream": dict(stats.by_workstream),
    }

    if stats.oldest_open:
        data["oldest_open"] = {
            "id": stats.oldest_open.id,
            "name": stats.oldest_open.name,
            "created": stats.oldest_open.created,
        }

    if stats.close_time:
        data["close_time"] = {
            "p50_days": stats.close_time.p50,
            "p75_days": stats.close_time.p75,
            "avg_days": stats.close_time.avg,
        }

    return json.dumps(data, indent=2)
