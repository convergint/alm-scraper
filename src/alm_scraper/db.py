"""Database access for defect queries."""

import sqlite3
from pathlib import Path

from alm_scraper.defect import Defect
from alm_scraper.storage import get_data_dir


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
    finally:
        conn.close()
