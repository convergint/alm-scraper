"""FastAPI backend for ALM web UI."""

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from lxml import html as lxml_html
from lxml_html_clean import Cleaner

from alm_scraper.db import (
    count_defects,
    get_defect_by_id,
    list_defects,
    search_defects,
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
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    """List defects with optional filtering and pagination."""
    offset = (page - 1) * limit

    # Use search if query provided
    if q:
        defects = search_defects(q, limit=limit)
        total = len(defects)  # TODO: get actual total from search
    else:
        defects = list_defects(
            status=(status,) if status else None,
            priority=(priority,) if priority else None,
            owner=(owner,) if owner else None,
            module=(module,) if module else None,
            defect_type=(defect_type,) if defect_type else None,
            workstream=(workstream,) if workstream else None,
            limit=limit,
            offset=offset,
        )
        # Get total count for pagination
        total = count_defects(
            status=(status,) if status else None,
            priority=(priority,) if priority else None,
            owner=(owner,) if owner else None,
            module=(module,) if module else None,
            defect_type=(defect_type,) if defect_type else None,
            workstream=(workstream,) if workstream else None,
        )

    pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "defects": [d.model_dump() for d in defects],
        "total": total,
        "page": page,
        "pages": pages,
    }


@app.get("/api/defects/{defect_id}")
async def get_defect(defect_id: int) -> dict:
    """Get a single defect by ID."""
    defect = get_defect_by_id(defect_id)
    if defect is None:
        raise HTTPException(status_code=404, detail="Defect not found")

    data = defect.model_dump()
    # Clean HTML fields (strip inline styles, unwrap font/span tags)
    data["description"] = clean_html(data.get("description"))
    # Format dev comments with structured author/date headers
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
