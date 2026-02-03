"""FastAPI backend for ALM web UI."""

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from lxml import html as lxml_html
from lxml_html_clean import Cleaner

from alm_scraper.constants import (
    KANBAN_HIDDEN_STATUSES,
    KANBAN_STATUS_ORDER,
    TERMINAL_STATUSES,
    AgeBuckets,
    DefectThresholds,
    format_convergint_owner,
)
from alm_scraper.db import (
    get_connection,
    get_defect_by_id,
    get_stats,
    list_defects,
    search_defects,
)
from alm_scraper.sql_helpers import (
    age_bucket_case_sql,
    age_days_sql,
    convergint_owner_filter,
    high_priority_filter,
    priority_sort_case_sql,
    terminal_status_filter,
)

# Tags to unwrap (remove tag but keep contents)
UNWRAP_TAGS = ["font", "span"]

# Tags that indicate actual HTML content
HTML_TAGS = re.compile(r"<(p|div|br|table|tr|td|ul|ol|li|h[1-6])\b", re.IGNORECASE)

# Pattern for comment separators (40 underscores, sometimes with period)
COMMENT_SEPARATOR = re.compile(r"_{10,}\.?\s*\n?")

# Pattern for comment author/date header
# Matches: "Name Name <username>, MM/DD/YYYY[format]:" or "username, MM/DD/YYYY:"
COMMENT_HEADER = re.compile(
    r"^([A-Za-z][A-Za-z0-9\s,.'()@<>_-]+?),?\s*"  # Author name
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"  # Date
    r"(?:\[([A-Za-z/\-]+)\])?"  # Optional format hint like [M/d/yyyy] - captured
    r"\s*:\s*",  # Colon separator
    re.MULTILINE,
)


def parse_date_to_iso(date_str: str, format_hint: str | None = None) -> str:
    """Parse a date string and return ISO 8601 format (YYYY-MM-DD)."""
    from datetime import datetime

    # Try format hint first
    format_map = {
        "M/d/yyyy": "%m/%d/%Y",
        "dd-MM-yyyy": "%d-%m-%Y",
        "yyyy-MM-dd": "%Y-%m-%d",
        "d/M/yyyy": "%d/%m/%Y",
    }

    if format_hint and format_hint in format_map:
        try:
            dt = datetime.strptime(date_str, format_map[format_hint])
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try common formats
    formats = [
        "%m/%d/%Y",  # 10/08/2025
        "%m/%d/%y",  # 10/08/25
        "%d-%m-%Y",  # 08-10-2025
        "%d-%m-%y",  # 08-10-25
        "%Y-%m-%d",  # 2025-10-08
        "%Y/%m/%d",  # 2025/10/08
        "%d/%m/%Y",  # 08/10/2025
        "%d/%m/%y",  # 08/10/25
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Sanity check: year should be reasonable (2020-2030)
            if 2020 <= dt.year <= 2030:
                return dt.strftime("%Y-%m-%d")
            # If 2-digit year parsed as 19xx, it's probably wrong format
            if dt.year < 2000:
                continue
        except ValueError:
            continue

    # If all parsing fails, return original
    return date_str


def format_dev_comments(content: str | None) -> str | None:
    """Format dev comments into structured HTML with author headers."""
    if not content:
        return content

    import html as html_module

    # Split by separator
    blocks = COMMENT_SEPARATOR.split(content)
    blocks = [b.strip() for b in blocks if b.strip()]

    if len(blocks) <= 1 and not COMMENT_HEADER.search(content):
        # No structure detected, just escape and convert newlines
        escaped = html_module.escape(content)
        return escaped.replace("\n", "<br>\n")

    result_parts = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Try to extract author/date header
        match = COMMENT_HEADER.match(block)
        if match:
            author = html_module.escape(match.group(1).strip())
            raw_date = match.group(2).strip()
            format_hint = match.group(3)  # May be None
            date = parse_date_to_iso(raw_date, format_hint)
            body = block[match.end() :].strip()
            body_html = html_module.escape(body).replace("\n", "<br>\n")

            result_parts.append(
                f'<div class="comment-block">'
                f'<div class="comment-header">'
                f'<span class="comment-author">{author}</span>'
                f'<span class="comment-date">{date}</span>'
                f"</div>"
                f'<div class="comment-body">{body_html}</div>'
                f"</div>"
            )
        else:
            # No header, just format the block
            body_html = html_module.escape(block).replace("\n", "<br>\n")
            result_parts.append(
                f'<div class="comment-block"><div class="comment-body">{body_html}</div></div>'
            )

    return "\n".join(result_parts)


def clean_html(content: str | None) -> str | None:
    """Clean HTML by stripping inline styles and unwanted tags, preserving structure.

    If content is plain text (no HTML tags), convert newlines to <br> tags.
    """
    if not content:
        return content

    import html as html_module

    # Check if this looks like HTML or plain text
    if not HTML_TAGS.search(content) and "<font" not in content.lower():
        # Plain text - just convert newlines to <br> and escape HTML
        escaped = html_module.escape(content)
        return escaped.replace("\n", "<br>\n")

    # Parse HTML
    doc = lxml_html.fragment_fromstring(content, create_parent="div")

    # Use lxml Cleaner to remove dangerous/unwanted content
    cleaner = Cleaner(
        scripts=True,
        javascript=True,
        style=True,
        inline_style=True,
        links=False,  # Keep <a> tags
        page_structure=False,
        safe_attrs_only=True,
        safe_attrs={"a": ["href"], "img": ["src", "alt"]},
    )
    doc = cleaner.clean_html(doc)

    # Unwrap font/span tags (keep their text content)
    for tag in UNWRAP_TAGS:
        for el in doc.iter(tag):
            el.drop_tag()

    # Convert back to HTML string
    cleaned_html = lxml_html.tostring(doc, encoding="unicode")
    # Remove the wrapper div we added
    cleaned_html = re.sub(r"^<div>|</div>$", "", cleaned_html)

    return cleaned_html


app = FastAPI(title="ALM Defects API")

# Allow CORS for dev server
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/defects")
async def get_defects(
    status: str | None = None,
    priority: str | None = None,
    owner: str | None = None,
    module: str | None = None,
    defect_type: str | None = None,
    workstream: str | None = None,
    scenario: str | None = None,
    blocking: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=5000),
) -> dict:
    """List defects with optional filtering and pagination."""
    offset = (page - 1) * limit

    # Build filter kwargs
    filters = {
        "status": (status,) if status else None,
        "priority": (priority,) if priority else None,
        "owner": (owner,) if owner else None,
        "module": (module,) if module else None,
        "defect_type": (defect_type,) if defect_type else None,
        "workstream": (workstream,) if workstream else None,
    }

    # Helper to filter by scenario codes
    def filter_by_scenario(defects: list, scenario: str | None, blocking: str | None) -> list:
        result = defects
        if scenario:
            result = [d for d in result if scenario in d.scenarios]
        if blocking:
            result = [d for d in result if blocking in d.blocks]
        return result

    # Use search if query provided, then apply filters
    if q:
        # Search returns all matches, we filter and paginate in memory
        all_results = search_defects(q, limit=500)  # Get more results to filter
        # Apply status filter (most common filter)
        if status:
            status_lower = status.lower()
            if status_lower == "!terminal":
                # Exclude terminal statuses (closed, rejected, duplicate, deferred)
                all_results = [
                    d for d in all_results if d.status and d.status.lower() not in TERMINAL_STATUSES
                ]
            elif status_lower == "!closed":
                # Exclude only closed status
                all_results = [d for d in all_results if d.status and d.status.lower() != "closed"]
            else:
                # Exact match
                all_results = [
                    d for d in all_results if d.status and d.status.lower() == status_lower
                ]
        if priority:
            all_results = [d for d in all_results if d.priority == priority]
        if owner:
            all_results = [d for d in all_results if d.owner and owner.lower() in d.owner.lower()]
        if workstream:
            all_results = [
                d
                for d in all_results
                if d.workstream and workstream.lower() in d.workstream.lower()
            ]
        if defect_type:
            all_results = [
                d
                for d in all_results
                if d.defect_type and defect_type.lower() in d.defect_type.lower()
            ]

        # Apply scenario filters
        all_results = filter_by_scenario(all_results, scenario, blocking)

        total = len(all_results)
        defects = all_results[offset : offset + limit]
    else:
        defects = list_defects(
            **filters,
            limit=None,  # Get all for scenario filtering
            offset=0,
        )
        # Apply scenario filters (done in memory since it's a list field)
        defects = filter_by_scenario(defects, scenario, blocking)
        total = len(defects)
        # Paginate
        defects = defects[offset : offset + limit]

    pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "defects": [d.model_dump() for d in defects],
        "total": total,
        "page": page,
        "pages": pages,
    }


@app.get("/api/scenarios")
async def get_scenarios() -> dict:
    """Get all unique scenario codes for filtering."""
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()
            cur.execute("SELECT scenarios FROM defects WHERE scenarios IS NOT NULL")
            all_scenarios: set[str] = set()
            all_blocks: set[str] = set()
            all_integrations: set[str] = set()

            cur.execute("SELECT scenarios, blocks, integrations FROM defects")
            for row in cur.fetchall():
                if row[0]:
                    all_scenarios.update(s.strip() for s in row[0].split(",") if s.strip())
                if row[1]:
                    all_blocks.update(s.strip() for s in row[1].split(",") if s.strip())
                if row[2]:
                    all_integrations.update(s.strip() for s in row[2].split(",") if s.strip())

            return {
                "scenarios": sorted(all_scenarios),
                "blocks": sorted(all_blocks),
                "integrations": sorted(all_integrations),
            }
    except FileNotFoundError:
        return {"scenarios": [], "blocks": [], "integrations": []}


@app.get("/api/burndown")
async def get_burndown() -> dict:
    """Get burndown/burnup chart data with trend prediction."""
    from datetime import datetime, timedelta

    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            # Get daily opened counts
            cur.execute("""
                SELECT date(created) as day, COUNT(*) as count
                FROM defects
                WHERE created IS NOT NULL
                GROUP BY date(created)
                ORDER BY day
            """)
            opened_by_day = {row[0]: row[1] for row in cur.fetchall()}

            # Get daily resolved counts (terminal statuses)
            # Use closed date for Closed status, modified date for others
            resolved_filter = terminal_status_filter(exclude=False)
            cur.execute(
                f"""
                SELECT date(COALESCE(closed, modified)) as day, COUNT(*) as count
                FROM defects
                WHERE {resolved_filter}
                  AND COALESCE(closed, modified) IS NOT NULL
                GROUP BY date(COALESCE(closed, modified))
                ORDER BY day
                """
            )
            closed_by_day = {row[0]: row[1] for row in cur.fetchall()}

            # Determine date range
            all_dates = set(opened_by_day.keys()) | set(closed_by_day.keys())
            if not all_dates:
                return {
                    "dates": [],
                    "cumulative_opened": [],
                    "cumulative_closed": [],
                    "open_count": [],
                    "prediction": None,
                }

            min_date = min(all_dates)
            max_date = max(all_dates)

            # Build cumulative arrays
            dates: list[str] = []
            cumulative_opened: list[int] = []
            cumulative_closed: list[int] = []
            open_count: list[int] = []

            current = datetime.strptime(min_date, "%Y-%m-%d")
            end = datetime.strptime(max_date, "%Y-%m-%d")
            total_opened = 0
            total_closed = 0

            while current <= end:
                day_str = current.strftime("%Y-%m-%d")
                total_opened += opened_by_day.get(day_str, 0)
                total_closed += closed_by_day.get(day_str, 0)

                dates.append(day_str)
                cumulative_opened.append(total_opened)
                cumulative_closed.append(total_closed)
                open_count.append(total_opened - total_closed)

                current += timedelta(days=1)

            # Calculate prediction based on recent trends (last 30 days)
            prediction = None
            if len(dates) >= 30:
                recent_days = 30
                recent_opened = cumulative_opened[-1] - cumulative_opened[-recent_days]
                recent_closed = cumulative_closed[-1] - cumulative_closed[-recent_days]

                daily_open_rate = recent_opened / recent_days
                daily_close_rate = recent_closed / recent_days
                net_burn_rate = daily_close_rate - daily_open_rate

                current_open = open_count[-1]
                pred_dates: list[str] = []
                pred_open: list[float] = []

                # Project forward up to 60 days
                pred_current = datetime.strptime(max_date, "%Y-%m-%d")
                projected_open = float(current_open)

                for _ in range(60):
                    pred_current += timedelta(days=1)
                    projected_open -= net_burn_rate
                    if projected_open < 0:
                        projected_open = 0

                    pred_dates.append(pred_current.strftime("%Y-%m-%d"))
                    pred_open.append(round(projected_open, 1))

                    # Stop if we've reached zero (burning down) or a cap (burning up)
                    if net_burn_rate > 0 and projected_open <= 0:
                        break
                    if net_burn_rate < 0 and projected_open > current_open * 2:
                        break

                prediction = {
                    "dates": pred_dates,
                    "open_count": pred_open,
                    "daily_open_rate": round(daily_open_rate, 2),
                    "daily_close_rate": round(daily_close_rate, 2),
                    "net_burn_rate": round(net_burn_rate, 2),
                }

            return {
                "dates": dates,
                "cumulative_opened": cumulative_opened,
                "cumulative_closed": cumulative_closed,
                "open_count": open_count,
                "prediction": prediction,
            }
    except FileNotFoundError:
        return {
            "dates": [],
            "cumulative_opened": [],
            "cumulative_closed": [],
            "open_count": [],
            "prediction": None,
        }


@app.get("/api/aging")
async def get_aging() -> dict:
    """Get aging analysis of active defects."""
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            active_filter = terminal_status_filter(exclude=True)
            age_bucket = age_bucket_case_sql("created")

            # Get age buckets for active defects
            cur.execute(f"""
                SELECT
                    {age_bucket} as bucket,
                    COUNT(*) as count
                FROM defects
                WHERE {active_filter} AND created IS NOT NULL
                GROUP BY bucket
            """)

            buckets = {"0-7 days": 0, "8-30 days": 0, "31-90 days": 0, "90+ days": 0}
            for row in cur.fetchall():
                buckets[row[0]] = row[1]

            # Get aging by priority with bucket breakdown
            age_expr = "julianday('now') - julianday(created)"
            cur.execute(f"""
                SELECT
                    priority,
                    SUM(CASE WHEN {age_expr} <= {AgeBuckets.VERY_NEW} THEN 1 ELSE 0 END),
                    SUM(CASE WHEN {age_expr} > {AgeBuckets.VERY_NEW}
                            AND {age_expr} <= {AgeBuckets.NEW} THEN 1 ELSE 0 END),
                    SUM(CASE WHEN {age_expr} > {AgeBuckets.NEW}
                            AND {age_expr} <= {AgeBuckets.MEDIUM} THEN 1 ELSE 0 END),
                    SUM(CASE WHEN {age_expr} > {AgeBuckets.MEDIUM} THEN 1 ELSE 0 END)
                FROM defects
                WHERE {active_filter} AND created IS NOT NULL
                GROUP BY priority
                ORDER BY priority
            """)
            by_priority = [
                {
                    "priority": row[0] or "(none)",
                    "0-7 days": row[1],
                    "8-30 days": row[2],
                    "31-90 days": row[3],
                    "90+ days": row[4],
                }
                for row in cur.fetchall()
            ]

            # Get oldest active defects
            age_days = age_days_sql("created")
            cur.execute(f"""
                SELECT id, name, created, priority,
                       {age_days} as age_days
                FROM defects
                WHERE {active_filter} AND created IS NOT NULL
                ORDER BY created ASC
                LIMIT 10
            """)
            oldest = [
                {
                    "id": row[0],
                    "name": row[1][:80],
                    "created": row[2],
                    "priority": row[3],
                    "age_days": row[4],
                }
                for row in cur.fetchall()
            ]

            return {
                "buckets": buckets,
                "by_priority": by_priority,
                "oldest": oldest,
            }
    except FileNotFoundError:
        return {"buckets": {}, "by_priority": [], "oldest": []}


@app.get("/api/velocity")
async def get_velocity() -> dict:
    """Get weekly velocity (opened vs resolved)."""
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            # Get weekly opened counts (last 12 weeks)
            cur.execute("""
                SELECT strftime('%Y-W%W', created) as week, COUNT(*) as count
                FROM defects
                WHERE created IS NOT NULL
                  AND created >= date('now', '-84 days')
                GROUP BY week
                ORDER BY week
            """)
            opened_by_week = {row[0]: row[1] for row in cur.fetchall()}

            # Get weekly resolved counts (terminal statuses)
            resolved_filter = terminal_status_filter(exclude=False)
            cur.execute(f"""
                SELECT strftime('%Y-W%W', COALESCE(closed, modified)) as week, COUNT(*) as count
                FROM defects
                WHERE {resolved_filter}
                  AND COALESCE(closed, modified) IS NOT NULL
                  AND COALESCE(closed, modified) >= date('now', '-84 days')
                GROUP BY week
                ORDER BY week
            """)
            resolved_by_week = {row[0]: row[1] for row in cur.fetchall()}

            # Combine into weekly data
            all_weeks = sorted(set(opened_by_week.keys()) | set(resolved_by_week.keys()))
            weeks = []
            for week in all_weeks:
                weeks.append(
                    {
                        "week": week,
                        "opened": opened_by_week.get(week, 0),
                        "resolved": resolved_by_week.get(week, 0),
                        "net": resolved_by_week.get(week, 0) - opened_by_week.get(week, 0),
                    }
                )

            # Calculate averages
            total_opened = sum(w["opened"] for w in weeks)
            total_resolved = sum(w["resolved"] for w in weeks)
            num_weeks = len(weeks) or 1

            return {
                "weeks": weeks,
                "avg_opened_per_week": round(total_opened / num_weeks, 1),
                "avg_resolved_per_week": round(total_resolved / num_weeks, 1),
                "avg_net_per_week": round((total_resolved - total_opened) / num_weeks, 1),
            }
    except FileNotFoundError:
        return {
            "weeks": [],
            "avg_opened_per_week": 0,
            "avg_resolved_per_week": 0,
            "avg_net_per_week": 0,
        }


@app.get("/api/priority-trend")
async def get_priority_trend() -> dict:
    """Get priority breakdown trend over time (weekly snapshots)."""
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            # For each week, count active defects by priority
            # This is approximate - we look at defects created before week end
            # and not resolved before week end
            active_filter = terminal_status_filter(exclude=True)
            cur.execute(f"""
                WITH RECURSIVE weeks AS (
                    SELECT date('now', '-77 days', 'weekday 0') as week_start
                    UNION ALL
                    SELECT date(week_start, '+7 days')
                    FROM weeks
                    WHERE week_start < date('now', '-7 days')
                )
                SELECT
                    w.week_start,
                    d.priority,
                    COUNT(*) as count
                FROM weeks w
                CROSS JOIN defects d
                WHERE d.created <= date(w.week_start, '+6 days')
                  AND (
                    {active_filter}
                    OR COALESCE(d.closed, d.modified) > date(w.week_start, '+6 days')
                  )
                GROUP BY w.week_start, d.priority
                ORDER BY w.week_start, d.priority
            """)

            # Organize by week
            weeks_data: dict[str, dict[str, int]] = {}
            for row in cur.fetchall():
                week = row[0]
                priority = row[1] or "(none)"
                count = row[2]
                if week not in weeks_data:
                    weeks_data[week] = {}
                weeks_data[week][priority] = count

            # Convert to list format
            weeks = []
            for week in sorted(weeks_data.keys()):
                data = weeks_data[week]
                weeks.append(
                    {
                        "week": week,
                        "P1": data.get("P1-Critical", 0),
                        "P2": data.get("P2-High", 0),
                        "P3": data.get("P3-Medium", 0),
                        "P4": data.get("P4-Low", 0),
                        "total": sum(data.values()),
                    }
                )

            return {"weeks": weeks}
    except FileNotFoundError:
        return {"weeks": []}


@app.get("/api/executive")
async def get_executive_summary() -> dict:
    """Get executive-level summary with ownership and actionable metrics."""
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            active_filter = terminal_status_filter(exclude=True)
            convergint_filter = convergint_owner_filter("owner")
            high_pri_filter = high_priority_filter("priority")
            age_days_created = age_days_sql("created")
            age_days_modified = age_days_sql("modified")

            # Ownership split (Convergint vs Vendor)
            cur.execute(f"""
                SELECT
                    CASE WHEN {convergint_filter}
                         THEN 'Convergint' ELSE 'Vendor' END as ownership,
                    COUNT(*) as active_count,
                    SUM(CASE WHEN priority = 'P1-Critical' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN priority = 'P2-High' THEN 1 ELSE 0 END)
                FROM defects
                WHERE {active_filter}
                GROUP BY ownership
            """)
            ownership = {}
            for row in cur.fetchall():
                ownership[row[0]] = {
                    "active": row[1],
                    "p1": row[2],
                    "p2": row[3],
                }

            # Status pipeline - where are active defects in the workflow
            cur.execute(f"""
                SELECT
                    status,
                    COUNT(*) as count,
                    ROUND(AVG({age_days_modified}), 1) as avg_days_stale
                FROM defects
                WHERE {active_filter}
                GROUP BY status
                ORDER BY count DESC
            """)
            pipeline = [
                {"status": row[0], "count": row[1], "avg_days_stale": row[2]}
                for row in cur.fetchall()
            ]

            # Blocked defects detail
            priority_sort = priority_sort_case_sql("priority")
            cur.execute(f"""
                SELECT id, name, owner, priority,
                       {age_days_created},
                       {age_days_modified}
                FROM defects
                WHERE LOWER(status) = 'blocked'
                ORDER BY {priority_sort}, 6 DESC
                LIMIT 10
            """)
            blocked = [
                {
                    "id": row[0],
                    "name": row[1][:60],
                    "owner": row[2],
                    "priority": row[3],
                    "age_days": row[4],
                    "days_stale": row[5],
                }
                for row in cur.fetchall()
            ]

            # Convergint owner scorecard
            cur.execute(f"""
                SELECT
                    owner,
                    COUNT(*) as active_count,
                    SUM(CASE WHEN {high_pri_filter} THEN 1 ELSE 0 END) as high_priority,
                    MAX({age_days_modified}),
                    ROUND(AVG({age_days_created}), 1)
                FROM defects
                WHERE {active_filter}
                  AND {convergint_filter}
                GROUP BY owner
                ORDER BY high_priority DESC, active_count DESC
            """)
            convergint_owners = [
                {
                    "owner": format_convergint_owner(row[0]),
                    "owner_raw": row[0],
                    "active": row[1],
                    "high_priority": row[2],
                    "max_days_stale": row[3],
                    "avg_age": row[4],
                }
                for row in cur.fetchall()
            ]

            # Stale Convergint defects (no update in 7+ days)
            cur.execute(f"""
                SELECT id, name, owner, priority, status,
                       {age_days_created} as age_days,
                       {age_days_modified} as days_stale
                FROM defects
                WHERE {active_filter}
                  AND {convergint_filter}
                  AND {age_days_modified} >= {DefectThresholds.STALE_DAYS}
                ORDER BY days_stale DESC
                LIMIT 10
            """)
            stale_convergint = [
                {
                    "id": row[0],
                    "name": row[1][:60],
                    "owner": format_convergint_owner(row[2]),
                    "priority": row[3],
                    "status": row[4],
                    "age_days": row[5],
                    "days_stale": row[6],
                }
                for row in cur.fetchall()
            ]

            # High priority not being worked (P1/P2 in New status for 2+ days)
            cur.execute(f"""
                SELECT id, name, owner, priority,
                       {age_days_created} as age_days
                FROM defects
                WHERE {active_filter}
                  AND {high_pri_filter}
                  AND LOWER(status) = 'new'
                  AND {age_days_created} >= {DefectThresholds.NEW_UNWORKED_DAYS}
                ORDER BY {priority_sort}, age_days DESC
                LIMIT 10
            """)
            high_priority_stale = [
                {
                    "id": row[0],
                    "name": row[1][:60],
                    "owner": row[2],
                    "priority": row[3],
                    "age_days": row[4],
                }
                for row in cur.fetchall()
            ]

            # Get blocked count from pipeline
            blocked_count = next(
                (p["count"] for p in pipeline if p["status"].lower() == "blocked"), 0
            )

            return {
                "ownership": ownership,
                "pipeline": pipeline,
                "blocked": blocked,
                "blocked_count": blocked_count,
                "convergint_owners": convergint_owners,
                "stale_convergint": stale_convergint,
                "high_priority_stale": high_priority_stale,
            }
    except FileNotFoundError:
        return {
            "ownership": {},
            "pipeline": [],
            "blocked": [],
            "blocked_count": 0,
            "convergint_owners": [],
            "stale_convergint": [],
            "high_priority_stale": [],
        }


@app.get("/api/kanban")
async def get_kanban(
    lane: str | None = None,
    include_hidden: bool = False,
) -> dict:
    """Get defects for kanban board view.

    Args:
        lane: Optional swimlane grouping field (priority, owner, module, workstream)
        include_hidden: If True, include hidden statuses (rejected, duplicate, deferred)

    Returns:
        columns: List of status columns in display order
        defects: List of defects (grouped by lane if specified)
        lanes: List of lane values if lane parameter provided
    """
    try:
        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()

            # Build status filter - exclude hidden statuses unless requested
            if include_hidden:
                status_filter = ""
            else:
                hidden_placeholders = ",".join(f"'{s}'" for s in KANBAN_HIDDEN_STATUSES)
                status_filter = f"WHERE LOWER(status) NOT IN ({hidden_placeholders})"

            # Get all matching defects
            cur.execute(f"""
                SELECT id, name, status, priority, owner, module, workstream,
                       created, modified
                FROM defects
                {status_filter}
            """)

            defects = []
            for row in cur.fetchall():
                defects.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "owner": row[4],
                        "module": row[5],
                        "workstream": row[6],
                        "created": row[7],
                        "modified": row[8],
                    }
                )

            # Determine which columns to show (only statuses that have defects)
            status_set = {d["status"] for d in defects if d["status"]}

            # Order columns according to KANBAN_STATUS_ORDER
            # Statuses not in the order list go at the end
            status_order_lower = [s.lower() for s in KANBAN_STATUS_ORDER]
            columns = []
            for status in KANBAN_STATUS_ORDER:
                if status.lower() in {s.lower() for s in status_set}:
                    columns.append(status)
            # Add any statuses not in the predefined order
            for status in sorted(status_set):
                if status.lower() not in status_order_lower:
                    columns.append(status)

            # Get lane values if swimlane grouping requested
            lanes: list[str] = []
            if lane and lane in ("priority", "owner", "module", "workstream"):
                lane_values = {d[lane] for d in defects if d.get(lane)}
                if lane == "priority":
                    # Sort priorities in logical order
                    priority_order = {"P1-Critical": 1, "P2-High": 2, "P3-Medium": 3, "P4-Low": 4}
                    lanes = sorted(lane_values, key=lambda p: priority_order.get(p, 99))
                else:
                    lanes = sorted(lane_values)

            return {
                "columns": columns,
                "defects": defects,
                "lanes": lanes,
                "lane_field": lane,
            }
    except FileNotFoundError:
        return {
            "columns": [],
            "defects": [],
            "lanes": [],
            "lane_field": lane,
        }


@app.get("/api/stats")
async def get_stats_endpoint(include_closed: bool = False) -> dict:
    """Get aggregate statistics about defects."""
    stats = get_stats(include_closed=include_closed, top_n=10)
    if stats is None:
        return {
            "total": 0,
            "open_count": 0,
            "closed_count": 0,
            "by_priority": [],
            "by_module": [],
            "by_owner": [],
            "by_type": [],
            "by_workstream": [],
            "oldest_open": None,
            "close_time": None,
            "by_scenario": [],
        }

    # Get scenario breakdown for active defects
    by_scenario: list[tuple[str, int]] = []
    try:
        active_filter = terminal_status_filter(exclude=True)

        with get_connection(row_factory=False) as conn:
            cur = conn.cursor()
            # Count defects per scenario (for active defects only)
            status_filter = "" if include_closed else f"WHERE {active_filter}"
            cur.execute(f"SELECT scenarios FROM defects {status_filter}")
            scenario_counts: dict[str, int] = {}
            for row in cur.fetchall():
                if row[0]:
                    for s in row[0].split(","):
                        s = s.strip()
                        if s:
                            scenario_counts[s] = scenario_counts.get(s, 0) + 1
            by_scenario = sorted(scenario_counts.items(), key=lambda x: -x[1])[:10]
    except FileNotFoundError:
        pass

    return {
        "total": stats.total,
        "open_count": stats.open_count,
        "closed_count": stats.closed_count,
        "by_priority": [{"name": name, "count": count} for name, count in stats.by_priority],
        "by_module": [{"name": name, "count": count} for name, count in stats.by_module],
        "by_owner": [{"name": name, "count": count} for name, count in stats.by_owner],
        "by_type": [{"name": name, "count": count} for name, count in stats.by_type],
        "by_workstream": [{"name": name, "count": count} for name, count in stats.by_workstream],
        "by_scenario": [{"name": name, "count": count} for name, count in by_scenario],
        "oldest_open": {
            "id": stats.oldest_open.id,
            "name": stats.oldest_open.name,
            "created": stats.oldest_open.created,
        }
        if stats.oldest_open
        else None,
        "close_time": {
            "p50": round(stats.close_time.p50, 1),
            "p75": round(stats.close_time.p75, 1),
            "avg": round(stats.close_time.avg, 1),
        }
        if stats.close_time
        else None,
    }


@app.get("/api/defects/{defect_id}")
async def get_defect(defect_id: int) -> dict:
    """Get a single defect by ID."""
    defect = get_defect_by_id(defect_id)
    if defect is None:
        raise HTTPException(status_code=404, detail="Defect not found")

    data = defect.model_dump()
    # Clean HTML fields (strip inline styles, unwrap font/span tags)
    # Use the HTML version if available, fall back to plain text
    data["description"] = clean_html(data.get("description_html") or data.get("description"))
    # For dev comments: use plain text version with format_dev_comments
    # which parses author/date headers and creates nice formatting with borders
    data["dev_comments"] = format_dev_comments(data.get("dev_comments"))
    return data


# Serve static files (built SvelteKit app) - only if directory exists and has content
static_dir = Path(__file__).parent / "static"
if static_dir.exists() and any(static_dir.iterdir()):
    # Mount static assets (js, css, etc.)
    app.mount("/_app", StaticFiles(directory=static_dir / "_app"), name="static_app")

    # Fallback: serve index.html for all non-API routes (SPA client-side routing)
    @app.get("/{path:path}")
    async def serve_spa(request: Request, path: str) -> FileResponse:
        """Serve index.html for client-side routing."""
        file_path = static_dir / path
        # If it's a real file, serve it
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(static_dir / "index.html")
