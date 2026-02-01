"""SQL building helpers for consistent query construction."""

from alm_scraper.constants import (
    CONVERGINT_OWNER_PATTERN,
    HIGH_PRIORITY_STATUSES,
    PRIORITY_ORDER,
    TERMINAL_STATUSES,
    AgeBuckets,
)


def terminal_status_filter(*, exclude: bool = True, use_placeholders: bool = False) -> str:
    """Build SQL fragment for filtering by terminal status.

    Args:
        exclude: If True, filter OUT terminal statuses (active defects).
                 If False, filter FOR terminal statuses (closed defects).
        use_placeholders: If True, use ? placeholders (for parameterized queries).
                          If False, use quoted string literals.

    Returns:
        SQL WHERE clause fragment (without WHERE keyword)

    Examples:
        >>> terminal_status_filter(exclude=True)
        "LOWER(status) NOT IN ('closed','rejected','duplicate','deferred')"
        >>> terminal_status_filter(exclude=False)
        "LOWER(status) IN ('closed','rejected','duplicate','deferred')"
    """
    if use_placeholders:
        placeholders = ",".join("?" * len(TERMINAL_STATUSES))
    else:
        placeholders = ",".join(f"'{s}'" for s in TERMINAL_STATUSES)

    operator = "NOT IN" if exclude else "IN"
    return f"LOWER(status) {operator} ({placeholders})"


def terminal_status_params() -> list[str]:
    """Get parameters for terminal status filter when using placeholders.

    Returns:
        List of terminal status strings for query parameters
    """
    return list(TERMINAL_STATUSES)


def age_bucket_case_sql(date_field: str = "created") -> str:
    """Build SQL CASE expression for age bucketing.

    Args:
        date_field: The date field to calculate age from

    Returns:
        SQL CASE expression that returns bucket labels
    """
    age = f"julianday('now') - julianday({date_field})"
    return f"""CASE
        WHEN {age} <= {AgeBuckets.VERY_NEW} THEN '0-7 days'
        WHEN {age} <= {AgeBuckets.NEW} THEN '8-30 days'
        WHEN {age} <= {AgeBuckets.MEDIUM} THEN '31-90 days'
        ELSE '90+ days'
    END"""


def age_days_sql(date_field: str = "created") -> str:
    """Build SQL expression for age in days as integer.

    Args:
        date_field: The date field to calculate age from

    Returns:
        SQL expression for age in days
    """
    return f"CAST(julianday('now') - julianday({date_field}) AS INTEGER)"


def age_expr_sql(date_field: str = "created") -> str:
    """Build SQL expression for age calculation (floating point).

    Args:
        date_field: The date field to calculate age from

    Returns:
        SQL expression for age as float
    """
    return f"julianday('now') - julianday({date_field})"


def priority_sort_case_sql(field: str = "priority") -> str:
    """Build SQL CASE expression for priority ordering.

    Args:
        field: The priority field name

    Returns:
        SQL CASE expression for ORDER BY
    """
    when_clauses = "\n".join(f"WHEN '{p}' THEN {order}" for p, order in PRIORITY_ORDER.items())
    return f"""CASE {field}
        {when_clauses}
        ELSE 999
    END"""


def high_priority_filter(field: str = "priority") -> str:
    """Build SQL fragment for filtering high priority defects.

    Args:
        field: The priority field name

    Returns:
        SQL WHERE clause fragment
    """
    quoted = ",".join(f"'{p}'" for p in HIGH_PRIORITY_STATUSES)
    return f"{field} IN ({quoted})"


def convergint_owner_filter(field: str = "owner") -> str:
    """Build SQL fragment for filtering Convergint-owned defects.

    Args:
        field: The owner field name

    Returns:
        SQL WHERE clause fragment
    """
    return f"{field} LIKE '{CONVERGINT_OWNER_PATTERN}'"


def build_in_clause(values: tuple[str, ...] | list[str], *, use_placeholders: bool = False) -> str:
    """Build an IN clause for a list of values.

    Args:
        values: List of values
        use_placeholders: If True, use ? placeholders; else use quoted literals

    Returns:
        IN clause string like "('a','b','c')" or "(?,?,?)"
    """
    if use_placeholders:
        placeholders = ",".join("?" * len(values))
    else:
        placeholders = ",".join(f"'{v}'" for v in values)
    return f"({placeholders})"
