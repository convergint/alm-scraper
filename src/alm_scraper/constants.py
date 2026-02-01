"""Shared business constants for the ALM scraper."""

# Terminal statuses - defects that are done and won't have more work
TERMINAL_STATUSES = ("closed", "rejected", "duplicate", "deferred")

# Priority ordering for sorting and display
PRIORITY_ORDER = {
    "P1-Critical": 1,
    "P2-High": 2,
    "P3-Medium": 3,
    "P4-Low": 4,
}

# High priority statuses that need attention
HIGH_PRIORITY_STATUSES = ("P1-Critical", "P2-High")


class DefectThresholds:
    """Thresholds for defect aging and staleness."""

    STALE_DAYS = 7  # No modification in 7+ days = stale
    NEW_UNWORKED_DAYS = 2  # P1/P2 in New status for 2+ days = needs attention
    RECENT_TREND_DAYS = 30  # Days to look back for trend calculations


class AgeBuckets:
    """Age bucket boundaries in days."""

    VERY_NEW = 7  # 0-7 days
    NEW = 30  # 8-30 days
    MEDIUM = 90  # 31-90 days
    # 90+ days is the remainder


# Convergint owner detection
CONVERGINT_OWNER_PATTERN = "%convergint%"


def format_convergint_owner(owner_raw: str) -> str:
    """Format Convergint owner email to display name.

    Args:
        owner_raw: Raw owner string like "john.doe_convergint.com"

    Returns:
        Formatted name like "John Doe"
    """
    return owner_raw.replace("_convergint.com", "").replace(".", " ").title()
