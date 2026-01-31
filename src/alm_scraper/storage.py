"""Local storage management for defect data."""

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from alm_scraper.defect import Defect


class SyncMeta(BaseModel):
    """Metadata about the current sync state."""

    last_sync: str
    defect_count: int
    current: str  # relative path to current history files (without extension)


def get_data_dir() -> Path:
    """Get the data directory path."""
    if env_dir := os.environ.get("ALM_DATA_DIR"):
        return Path(env_dir)
    return Path.home() / ".local" / "share" / "alm-scraper"


def get_history_dir() -> Path:
    """Get the history directory path."""
    return get_data_dir() / "history"


def generate_timestamp() -> str:
    """Generate a timestamp string for file naming."""
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


def write_defects_json(defects: list[Defect], path: Path) -> None:
    """Write defects to a JSON file.

    Args:
        defects: List of defects to write.
        path: Path to write to.
    """
    data = [d.model_dump() for d in defects]
    with path.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def build_sqlite_db(defects: list[Defect], db_path: Path) -> None:
    """Build SQLite database with FTS5 from defects.

    Args:
        defects: List of defects to index.
        db_path: Path to the database file.
    """
    # Remove existing file if present
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # Create main defects table
        cur.execute("""
            CREATE TABLE defects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT,
                priority TEXT,
                severity TEXT,
                owner TEXT,
                detected_by TEXT,
                description TEXT,
                description_html TEXT,
                dev_comments TEXT,
                dev_comments_html TEXT,
                created TEXT,
                modified TEXT,
                closed TEXT,
                reproducible TEXT,
                attachment TEXT,
                detected_in_rel TEXT,
                detected_in_rcyc TEXT,
                actual_fix_time INTEGER,
                defect_type TEXT,
                application TEXT,
                workstream TEXT,
                module TEXT,
                target_date TEXT
            )
        """)

        # Create FTS5 virtual table for full-text search
        cur.execute("""
            CREATE VIRTUAL TABLE defects_fts USING fts5(
                name,
                description,
                dev_comments,
                owner,
                detected_by,
                content='defects',
                content_rowid='id'
            )
        """)

        # Insert defects
        for defect in defects:
            cur.execute(
                """
                INSERT INTO defects (
                    id, name, status, priority, severity, owner, detected_by,
                    description, description_html, dev_comments, dev_comments_html,
                    created, modified, closed, reproducible, attachment,
                    detected_in_rel, detected_in_rcyc, actual_fix_time,
                    defect_type, application, workstream, module, target_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    defect.id,
                    defect.name,
                    defect.status,
                    defect.priority,
                    defect.severity,
                    defect.owner,
                    defect.detected_by,
                    defect.description,
                    defect.description_html,
                    defect.dev_comments,
                    defect.dev_comments_html,
                    defect.created,
                    defect.modified,
                    defect.closed,
                    defect.reproducible,
                    defect.attachment,
                    defect.detected_in_rel,
                    defect.detected_in_rcyc,
                    defect.actual_fix_time,
                    defect.defect_type,
                    defect.application,
                    defect.workstream,
                    defect.module,
                    defect.target_date,
                ),
            )

        # Populate FTS index
        cur.execute("""
            INSERT INTO defects_fts(defects_fts) VALUES('rebuild')
        """)

        # Create indexes for common queries
        cur.execute("CREATE INDEX idx_status ON defects(status)")
        cur.execute("CREATE INDEX idx_owner ON defects(owner)")
        cur.execute("CREATE INDEX idx_priority ON defects(priority)")

        conn.commit()
    finally:
        conn.close()


def update_symlinks(data_dir: Path, history_base: str) -> None:
    """Update symlinks to point to the latest sync.

    Args:
        data_dir: The data directory (~/.local/share/alm-scraper).
        history_base: Base name in history dir (e.g., "history/defects-20260130-2253").
    """
    json_link = data_dir / "defects.json"
    db_link = data_dir / "defects.db"

    # Remove old symlinks if they exist
    for link in (json_link, db_link):
        if link.is_symlink() or link.exists():
            link.unlink()

    # Create new symlinks (relative paths)
    json_link.symlink_to(f"{history_base}.json")
    db_link.symlink_to(f"{history_base}.db")


def write_sync_meta(data_dir: Path, defect_count: int, history_base: str) -> None:
    """Write sync metadata file.

    Args:
        data_dir: The data directory.
        defect_count: Number of defects synced.
        history_base: Base name in history dir.
    """
    meta = SyncMeta(
        last_sync=datetime.now(UTC).isoformat(),
        defect_count=defect_count,
        current=history_base,
    )

    meta_path = data_dir / "sync_meta.json"
    with meta_path.open("w") as f:
        json.dump(meta.model_dump(), f, indent=2)
        f.write("\n")


class SyncResult(BaseModel, arbitrary_types_allowed=True):
    """Result of a sync operation."""

    data_dir: Path
    history_base: str
    defect_count: int


def sync_defects(defects: list[Defect]) -> SyncResult:
    """Sync defects to local storage.

    This performs the full sync operation:
    1. Delete any stale .tmp files
    2. Write history/defects-{timestamp}.json.tmp
    3. Build history/defects-{timestamp}.db.tmp
    4. Rename to drop .tmp suffix
    5. Update symlinks
    6. Update sync_meta.json

    Args:
        defects: List of defects to sync.

    Returns:
        SyncResult with data_dir, history_base, and defect_count.
    """
    data_dir = get_data_dir()
    history_dir = get_history_dir()

    # Ensure directories exist
    data_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = generate_timestamp()
    history_base = f"history/defects-{timestamp}"

    json_tmp = history_dir / f"defects-{timestamp}.json.tmp"
    db_tmp = history_dir / f"defects-{timestamp}.db.tmp"
    json_final = history_dir / f"defects-{timestamp}.json"
    db_final = history_dir / f"defects-{timestamp}.db"

    # Clean up any stale tmp files
    for tmp_file in history_dir.glob("*.tmp"):
        tmp_file.unlink()

    # Write JSON
    write_defects_json(defects, json_tmp)

    # Build SQLite
    build_sqlite_db(defects, db_tmp)

    # Atomic rename
    json_tmp.rename(json_final)
    db_tmp.rename(db_final)

    # Update symlinks
    update_symlinks(data_dir, history_base)

    # Write metadata
    write_sync_meta(data_dir, len(defects), history_base)

    return SyncResult(
        data_dir=data_dir,
        history_base=history_base,
        defect_count=len(defects),
    )
