"""Database access for defect queries."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from alm_scraper.defect import Defect
from alm_scraper.storage import get_data_dir


def get_db_path() -> Path:
    """Get path to the current defects database."""
    return get_data_dir() / "defects.db"


@contextmanager
def get_connection(
    row_factory: bool = True,
) -> Generator[sqlite3.Connection]:
    """Context manager for database connections.

    Args:
        row_factory: If True, use sqlite3.Row for dict-like access.

    Yields:
        Database connection.

    Raises:
        FileNotFoundError: If database doesn't exist.
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    if row_factory:
        conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _add_exact_filter(
    conditions: list[str],
    params: list[str],
    field: str,
    values: tuple[str, ...],
) -> None:
    """Add exact match filter (case-insensitive IN clause)."""
    if values:
        placeholders = ",".join("?" * len(values))
        conditions.append(f"LOWER({field}) IN ({placeholders})")
        params.extend(v.lower() for v in values)


def _add_partial_filter(
    conditions: list[str],
    params: list[str],
    field: str,
    values: tuple[str, ...],
) -> None:
    """Add partial match filter (case-insensitive LIKE with OR)."""
    if values:
        like_conditions = [f"LOWER({field}) LIKE ?" for _ in values]
        conditions.append(f"({' OR '.join(like_conditions)})")
        params.extend(f"%{v.lower()}%" for v in values)


def _row_to_defect(row: sqlite3.Row) -> Defect:
    """Convert a database row to a Defect object."""
    return Defect(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        priority=row["priority"],
        severity=row["severity"],
        owner=row["owner"],
        detected_by=row["detected_by"],
        description=row["description"],
        description_html=row["description_html"],
        dev_comments=row["dev_comments"],
        dev_comments_html=row["dev_comments_html"],
        created=row["created"],
        modified=row["modified"],
        closed=row["closed"],
        reproducible=row["reproducible"],
        attachment=row["attachment"],
        detected_in_rel=row["detected_in_rel"],
        detected_in_rcyc=row["detected_in_rcyc"],
        actual_fix_time=row["actual_fix_time"],
        defect_type=row["defect_type"],
        application=row["application"],
        workstream=row["workstream"],
        module=row["module"],
        target_date=row["target_date"],
    )


def get_defect_by_id(defect_id: int) -> Defect | None:
    """Fetch a defect by ID from the database.

    Args:
        defect_id: The defect ID to look up.

    Returns:
        Defect if found, None otherwise.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM defects WHERE id = ?", (defect_id,))
            row = cur.fetchone()
            return _row_to_defect(row) if row else None
    except FileNotFoundError:
        return None


def _build_filter_query(
    status: tuple[str, ...] | None = None,
    owner: tuple[str, ...] | None = None,
    module: tuple[str, ...] | None = None,
    defect_type: tuple[str, ...] | None = None,
    priority: tuple[str, ...] | None = None,
    workstream: tuple[str, ...] | None = None,
) -> tuple[str, list[str]]:
    """Build WHERE clause and params for defect filters."""
    conditions: list[str] = []
    params: list[str] = []

    # Exact match filters
    if status:
        _add_exact_filter(conditions, params, "status", status)
    if priority:
        _add_exact_filter(conditions, params, "priority", priority)

    # Partial match filters
    if owner:
        _add_partial_filter(conditions, params, "owner", owner)
    if module:
        _add_partial_filter(conditions, params, "module", module)
    if defect_type:
        _add_partial_filter(conditions, params, "defect_type", defect_type)
    if workstream:
        _add_partial_filter(conditions, params, "workstream", workstream)

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


def list_defects(
    status: tuple[str, ...] | None = None,
    owner: tuple[str, ...] | None = None,
    module: tuple[str, ...] | None = None,
    defect_type: tuple[str, ...] | None = None,
    priority: tuple[str, ...] | None = None,
    workstream: tuple[str, ...] | None = None,
    limit: int | None = 50,
    offset: int = 0,
) -> list[Defect]:
    """List defects with optional filters.

    All filters are AND'd together. Multiple values within a filter are OR'd.

    Args:
        status: Filter by status (case-insensitive exact match).
        owner: Filter by owner (case-insensitive partial match).
        module: Filter by module (case-insensitive partial match).
        defect_type: Filter by defect type (case-insensitive partial match).
        priority: Filter by priority (case-insensitive exact match).
        workstream: Filter by workstream (case-insensitive partial match).
        limit: Maximum results to return (None for no limit).
        offset: Number of results to skip.

    Returns:
        List of matching defects, sorted by priority then created date.
    """
    try:
        with get_connection() as conn:
            where, params = _build_filter_query(
                status=status,
                owner=owner,
                module=module,
                defect_type=defect_type,
                priority=priority,
                workstream=workstream,
            )

            query = f"""
                SELECT * FROM defects
                WHERE {where}
                ORDER BY priority ASC, created ASC
            """

            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([str(limit), str(offset)])

            cur = conn.cursor()
            cur.execute(query, params)
            return [_row_to_defect(row) for row in cur.fetchall()]
    except FileNotFoundError:
        return []


def count_defects(
    status: tuple[str, ...] | None = None,
    owner: tuple[str, ...] | None = None,
    module: tuple[str, ...] | None = None,
    defect_type: tuple[str, ...] | None = None,
    priority: tuple[str, ...] | None = None,
    workstream: tuple[str, ...] | None = None,
) -> int:
    """Return total number of defects matching filters."""
    try:
        with get_connection(row_factory=False) as conn:
            where, params = _build_filter_query(
                status=status,
                owner=owner,
                module=module,
                defect_type=defect_type,
                priority=priority,
                workstream=workstream,
            )
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM defects WHERE {where}", params)
            return cur.fetchone()[0]
    except FileNotFoundError:
        return 0


def search_defects(query: str, limit: int = 50) -> list[Defect]:
    """Full-text search across defects using FTS5.

    Args:
        query: Search query string.
        limit: Maximum results to return.

    Returns:
        List of matching defects, ranked by relevance.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            # Add * to each word for prefix matching (e.g., "rob" matches "robert")
            # Escape quotes and split into words
            words = query.replace('"', "").split()
            if not words:
                return []
            # Make each word a prefix search
            fts_query = " ".join(f'"{word}"*' for word in words)

            cur.execute(
                """
                SELECT d.* FROM defects d
                JOIN defects_fts fts ON d.id = fts.rowid
                WHERE defects_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit),
            )
            return [_row_to_defect(row) for row in cur.fetchall()]
    except FileNotFoundError:
        return []


class OldestDefect:
    """Summary of the oldest open defect."""

    def __init__(self, id: int, name: str, created: str) -> None:
        self.id = id
        self.name = name
        self.created = created


class CloseTimeStats:
    """Statistics about defect close times."""

    def __init__(self, p50: float, p75: float, avg: float) -> None:
        self.p50 = p50  # median, in days
        self.p75 = p75  # 75th percentile, in days
        self.avg = avg  # average, in days


class Stats:
    """Aggregate statistics about defects."""

    def __init__(
        self,
        total: int,
        open_count: int,
        closed_count: int,
        by_priority: list[tuple[str, int]],
        by_module: list[tuple[str, int]],
        by_owner: list[tuple[str, int]],
        by_type: list[tuple[str, int]],
        by_workstream: list[tuple[str, int]],
        oldest_open: OldestDefect | None = None,
        close_time: CloseTimeStats | None = None,
    ) -> None:
        self.total = total
        self.open_count = open_count
        self.closed_count = closed_count
        self.by_priority = by_priority
        self.by_module = by_module
        self.by_owner = by_owner
        self.by_type = by_type
        self.by_workstream = by_workstream
        self.oldest_open = oldest_open
        self.close_time = close_time


def _get_breakdown(
    cur: sqlite3.Cursor,
    field: str,
    status_filter: str,
    limit: int | None = None,
) -> list[tuple[str, int]]:
    """Get count breakdown by field."""
    query = f"""
        SELECT {field}, COUNT(*) as count
        FROM defects {status_filter}
        GROUP BY {field}
        ORDER BY count DESC
    """
    if limit:
        cur.execute(query + " LIMIT ?", (limit,))
    else:
        cur.execute(query)
    return [(row[0] or "(none)", row[1]) for row in cur.fetchall()]


def get_stats(include_closed: bool = False, top_n: int = 5) -> Stats | None:
    """Get aggregate statistics about defects.

    Args:
        include_closed: Include closed defects in breakdowns (default: open only).
        top_n: Number of items to include in each breakdown.

    Returns:
        Stats object, or None if no database exists.
    """
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            # Total counts (always show both)
            cur.execute("SELECT COUNT(*) FROM defects")
            total = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM defects WHERE LOWER(status) = 'open'")
            open_count = cur.fetchone()[0]

            closed_count = total - open_count

            # Status filter for breakdowns
            status_filter = "" if include_closed else "WHERE LOWER(status) = 'open'"

            # Get breakdowns
            by_priority = _get_breakdown(cur, "priority", status_filter)
            by_priority.sort(key=lambda x: x[0])  # Sort by priority name
            by_module = _get_breakdown(cur, "module", status_filter, top_n)
            by_owner = _get_breakdown(cur, "owner", status_filter, top_n)
            by_type = _get_breakdown(cur, "defect_type", status_filter, top_n)
            by_workstream = _get_breakdown(cur, "workstream", status_filter, top_n)

            # Oldest open defect
            oldest_open = None
            cur.execute("""
                SELECT id, name, created
                FROM defects
                WHERE LOWER(status) = 'open' AND created IS NOT NULL
                ORDER BY created ASC
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                oldest_open = OldestDefect(id=row[0], name=row[1], created=row[2])

            # Close time stats (for defects with both created and closed dates)
            close_time = None
            cur.execute("""
                SELECT julianday(closed) - julianday(created) as days
                FROM defects
                WHERE closed IS NOT NULL AND created IS NOT NULL
                ORDER BY days ASC
            """)
            close_days = [row[0] for row in cur.fetchall() if row[0] is not None and row[0] >= 0]

            if close_days:
                n = len(close_days)
                p50 = close_days[n // 2]
                p75 = close_days[min(int(n * 0.75), n - 1)]
                avg = sum(close_days) / n
                close_time = CloseTimeStats(p50=p50, p75=p75, avg=avg)

            return Stats(
                total=total,
                open_count=open_count,
                closed_count=closed_count,
                by_priority=by_priority,
                by_module=by_module,
                by_owner=by_owner,
                by_type=by_type,
                by_workstream=by_workstream,
                oldest_open=oldest_open,
                close_time=close_time,
            )
    except FileNotFoundError:
        return None
