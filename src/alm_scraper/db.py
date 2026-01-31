"""Database access for defect queries."""

import sqlite3
from pathlib import Path

from alm_scraper.defect import Defect
from alm_scraper.storage import get_data_dir


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


def get_db_path() -> Path:
    """Get path to the current defects database."""
    return get_data_dir() / "defects.db"


def get_defect_by_id(defect_id: int) -> Defect | None:
    """Fetch a defect by ID from the database.

    Args:
        defect_id: The defect ID to look up.

    Returns:
        Defect if found, None otherwise.
    """
    db_path = get_db_path()

    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM defects WHERE id = ?", (defect_id,))
        row = cur.fetchone()

        if not row:
            return None

        return _row_to_defect(row)
    finally:
        conn.close()


def list_defects(
    status: tuple[str, ...] = (),
    owner: tuple[str, ...] = (),
    module: tuple[str, ...] = (),
    defect_type: tuple[str, ...] = (),
    priority: tuple[str, ...] = (),
    workstream: tuple[str, ...] = (),
    limit: int | None = 50,
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

    Returns:
        List of matching defects, sorted by priority then created date.
    """
    db_path = get_db_path()

    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conditions: list[str] = []
        params: list[str] = []

        # Exact match filters (case-insensitive)
        if status:
            placeholders = ",".join("?" * len(status))
            conditions.append(f"LOWER(status) IN ({placeholders})")
            params.extend(s.lower() for s in status)

        if priority:
            placeholders = ",".join("?" * len(priority))
            conditions.append(f"LOWER(priority) IN ({placeholders})")
            params.extend(p.lower() for p in priority)

        # Partial match filters (case-insensitive LIKE)
        if owner:
            owner_conditions = ["LOWER(owner) LIKE ?" for _ in owner]
            conditions.append(f"({' OR '.join(owner_conditions)})")
            params.extend(f"%{o.lower()}%" for o in owner)

        if module:
            module_conditions = ["LOWER(module) LIKE ?" for _ in module]
            conditions.append(f"({' OR '.join(module_conditions)})")
            params.extend(f"%{m.lower()}%" for m in module)

        if defect_type:
            type_conditions = ["LOWER(defect_type) LIKE ?" for _ in defect_type]
            conditions.append(f"({' OR '.join(type_conditions)})")
            params.extend(f"%{t.lower()}%" for t in defect_type)

        if workstream:
            ws_conditions = ["LOWER(workstream) LIKE ?" for _ in workstream]
            conditions.append(f"({' OR '.join(ws_conditions)})")
            params.extend(f"%{w.lower()}%" for w in workstream)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM defects
            WHERE {where}
            ORDER BY priority ASC, created ASC
        """

        if limit is not None:
            query += " LIMIT ?"
            params.append(str(limit))

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

        return [_row_to_defect(row) for row in rows]
    finally:
        conn.close()


def count_defects() -> int:
    """Return total number of defects in the database."""
    db_path = get_db_path()

    if not db_path.exists():
        return 0

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM defects")
        return cur.fetchone()[0]
    finally:
        conn.close()


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


def get_stats(include_closed: bool = False, top_n: int = 5) -> Stats | None:
    """Get aggregate statistics about defects.

    Args:
        include_closed: Include closed defects in breakdowns (default: open only).
        top_n: Number of items to include in each breakdown.

    Returns:
        Stats object, or None if no database exists.
    """
    db_path = get_db_path()

    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # Total counts (always show both)
        cur.execute("SELECT COUNT(*) FROM defects")
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM defects WHERE LOWER(status) = 'open'")
        open_count = cur.fetchone()[0]

        closed_count = total - open_count

        # Status filter for breakdowns
        status_filter = "" if include_closed else "WHERE LOWER(status) = 'open'"

        # By priority (show all, sorted by priority)
        cur.execute(f"""
            SELECT priority, COUNT(*) as count
            FROM defects {status_filter}
            GROUP BY priority
            ORDER BY priority ASC
        """)
        by_priority = [(row[0] or "(none)", row[1]) for row in cur.fetchall()]

        # By module (top N)
        cur.execute(
            f"""
            SELECT module, COUNT(*) as count
            FROM defects {status_filter}
            GROUP BY module
            ORDER BY count DESC
            LIMIT ?
        """,
            (top_n,),
        )
        by_module = [(row[0] or "(none)", row[1]) for row in cur.fetchall()]

        # By owner (top N)
        cur.execute(
            f"""
            SELECT owner, COUNT(*) as count
            FROM defects {status_filter}
            GROUP BY owner
            ORDER BY count DESC
            LIMIT ?
        """,
            (top_n,),
        )
        by_owner = [(row[0] or "(none)", row[1]) for row in cur.fetchall()]

        # By type (top N)
        cur.execute(
            f"""
            SELECT defect_type, COUNT(*) as count
            FROM defects {status_filter}
            GROUP BY defect_type
            ORDER BY count DESC
            LIMIT ?
        """,
            (top_n,),
        )
        by_type = [(row[0] or "(none)", row[1]) for row in cur.fetchall()]

        # By workstream (top N)
        cur.execute(
            f"""
            SELECT workstream, COUNT(*) as count
            FROM defects {status_filter}
            GROUP BY workstream
            ORDER BY count DESC
            LIMIT ?
        """,
            (top_n,),
        )
        by_workstream = [(row[0] or "(none)", row[1]) for row in cur.fetchall()]

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
            p50_idx = n // 2
            p75_idx = int(n * 0.75)

            p50 = close_days[p50_idx]
            p75 = close_days[min(p75_idx, n - 1)]
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
    finally:
        conn.close()
