"""SQL query execution and schema documentation."""

import csv
import io
import json

from alm_scraper.db import get_connection

# Column descriptions for schema documentation
COLUMN_DOCS = {
    "id": "Defect ID (e.g., 993)",
    "name": "Defect title/summary",
    "status": "Open, Closed, Rejected, etc.",
    "priority": "P1-Critical, P2-High, P3-Medium, P4-Low",
    "severity": "Severity level",
    "owner": "Assigned owner (username or email)",
    "detected_by": "Who reported it",
    "description": "Plain text description (HTML stripped)",
    "description_html": "Original HTML description",
    "dev_comments": "Plain text dev comments (HTML stripped)",
    "dev_comments_html": "Original HTML dev comments",
    "created": "Creation date (YYYY-MM-DD)",
    "modified": "Last modified (YYYY-MM-DD HH:MM:SS)",
    "closed": "Close date (YYYY-MM-DD) or NULL if open",
    "defect_type": "Type (01_Code, 02_Configuration, 03_Data Error, etc.)",
    "workstream": "Workstream name",
    "module": "Module name (Data, Configuration, Functional, Integration)",
    "application": "Application name",
    "reproducible": "Is defect reproducible",
    "attachment": "Attachment info",
    "detected_in_rel": "Detected in release",
    "detected_in_rcyc": "Detected in release cycle",
    "actual_fix_time": "Actual fix time",
    "target_date": "Target fix date",
}

SCHEMA_HELP = """
SCHEMA:

Table: defects
{columns}

Table: defects_fts (full-text search)
  FTS5 virtual table for searching name, description, dev_comments.
  Use: SELECT * FROM defects_fts WHERE defects_fts MATCH 'search term'
  Join with defects: JOIN defects d ON d.id = defects_fts.rowid

EXAMPLES:

  # Find open P1 defects
  alm query "SELECT id, name, owner FROM defects
             WHERE status = 'Open' AND priority = 'P1-Critical'"

  # Defects closed in the last 7 days
  alm query "SELECT id, name, closed FROM defects
             WHERE closed >= date('now', '-7 days') ORDER BY closed DESC"

  # Full-text search for 'invoice'
  alm query "SELECT d.id, d.name, d.status FROM defects d
             JOIN defects_fts f ON d.id = f.rowid
             WHERE defects_fts MATCH 'invoice'"

  # Average close time by workstream
  alm query "SELECT workstream,
                    ROUND(AVG(julianday(closed) - julianday(created)), 1) as avg_days
             FROM defects WHERE closed IS NOT NULL
             GROUP BY workstream ORDER BY avg_days"

  # Count by status
  alm query "SELECT status, COUNT(*) as count FROM defects GROUP BY status"
"""


def get_schema_help() -> str:
    """Generate schema documentation."""
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.execute("PRAGMA table_info(defects)")
            rows = cur.fetchall()

            lines = []
            for row in rows:
                col_name = row[1]
                col_type = row[2] or "TEXT"
                desc = COLUMN_DOCS.get(col_name, "")
                if desc:
                    lines.append(f"  {col_name:20} {col_type:10} -- {desc}")
                else:
                    lines.append(f"  {col_name:20} {col_type}")

            columns = "\n".join(lines)
            return SCHEMA_HELP.format(columns=columns)
    except FileNotFoundError:
        # Return static schema if no DB exists yet
        columns = "\n".join(f"  {col:20} -- {desc}" for col, desc in COLUMN_DOCS.items())
        return SCHEMA_HELP.format(columns=columns)


def is_safe_query(sql: str) -> bool:
    """Check if query is read-only (SELECT, WITH, EXPLAIN)."""
    normalized = sql.strip().upper()
    return (
        normalized.startswith("SELECT")
        or normalized.startswith("WITH")
        or normalized.startswith("EXPLAIN")
    )


class QueryResult:
    """Result of a SQL query."""

    def __init__(self, columns: list[str], rows: list[tuple]) -> None:
        self.columns = columns
        self.rows = rows

    def to_table(self) -> str:
        """Format as aligned text table."""
        if not self.rows:
            return "(no results)"

        # Calculate column widths
        widths = [len(col) for col in self.columns]
        for row in self.rows:
            for i, val in enumerate(row):
                val_str = str(val) if val is not None else "NULL"
                # Truncate long values for display
                if len(val_str) > 60:
                    val_str = val_str[:57] + "..."
                widths[i] = max(widths[i], len(val_str))

        # Build table
        lines = []

        # Header
        header = "  ".join(col.ljust(widths[i]) for i, col in enumerate(self.columns))
        lines.append(header)
        lines.append("  ".join("-" * w for w in widths))

        # Rows
        for row in self.rows:
            row_strs = []
            for i, val in enumerate(row):
                val_str = str(val) if val is not None else "NULL"
                if len(val_str) > 60:
                    val_str = val_str[:57] + "..."
                row_strs.append(val_str.ljust(widths[i]))
            lines.append("  ".join(row_strs))

        return "\n".join(lines)

    def to_csv(self) -> str:
        """Format as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.columns)
        writer.writerows(self.rows)
        return output.getvalue()

    def to_json(self) -> str:
        """Format as JSON array of objects."""
        data = [dict(zip(self.columns, row, strict=True)) for row in self.rows]
        return json.dumps(data, indent=2, default=str)


def execute_query(sql: str) -> QueryResult:
    """Execute a SQL query and return results.

    Args:
        sql: SQL query to execute.

    Returns:
        QueryResult with columns and rows.

    Raises:
        ValueError: If query is not read-only.
        sqlite3.Error: If query fails.
        FileNotFoundError: If database doesn't exist.
    """
    if not is_safe_query(sql):
        raise ValueError("Only SELECT, WITH, and EXPLAIN queries are allowed")

    with get_connection(row_factory=False) as conn:
        cur = conn.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
        return QueryResult(columns=columns, rows=rows)
