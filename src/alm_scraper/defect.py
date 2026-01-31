"""Defect model and ALM data parsing."""

import html.parser
import re
from typing import Any

from pydantic import BaseModel


class Defect(BaseModel):
    """Normalized defect record."""

    id: int
    name: str
    status: str | None = None
    priority: str | None = None
    severity: str | None = None
    owner: str | None = None
    detected_by: str | None = None
    description: str | None = None
    description_html: str | None = None
    dev_comments: str | None = None
    dev_comments_html: str | None = None
    created: str | None = None
    modified: str | None = None
    closed: str | None = None

    # Additional fields we preserve
    reproducible: str | None = None
    attachment: str | None = None
    detected_in_rel: str | None = None
    detected_in_rcyc: str | None = None
    actual_fix_time: int | None = None

    # Custom fields (user-template-XX mapped to readable names where known)
    defect_type: str | None = None  # user-template-08
    application: str | None = None  # user-01
    workstream: str | None = None  # user-template-02
    module: str | None = None  # user-template-03
    target_date: str | None = None  # user-template-12


class HTMLTextExtractor(html.parser.HTMLParser):
    """Extract plain text from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)


def strip_html(html_content: str | None) -> str | None:
    """Strip HTML tags and return plain text."""
    if not html_content:
        return None

    parser = HTMLTextExtractor()
    try:
        parser.feed(html_content)
        text = parser.get_text()
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text if text else None
    except Exception:
        # If parsing fails, return original
        return html_content


def parse_alm_entity(entity: dict[str, Any]) -> Defect:
    """Parse an ALM entity into a normalized Defect.

    Args:
        entity: Raw entity dict from ALM API with Fields array.

    Returns:
        Normalized Defect object.
    """
    # Build a lookup from field name to value
    fields: dict[str, str | None] = {}

    for field in entity.get("Fields", []):
        name = field.get("Name", "")
        values = field.get("values", [])

        # Extract the value - handle empty arrays, empty objects, and actual values
        if not values:
            fields[name] = None
        elif isinstance(values[0], dict):
            fields[name] = values[0].get("value")
        else:
            fields[name] = None

    # Parse required fields
    defect_id = int(fields.get("id") or 0)
    name = fields.get("name") or ""

    # Parse optional fields
    description_html = fields.get("description")
    dev_comments_html = fields.get("dev-comments")

    # Parse actual-fix-time as int
    fix_time_str = fields.get("actual-fix-time")
    actual_fix_time = int(fix_time_str) if fix_time_str else None

    return Defect(
        id=defect_id,
        name=name,
        status=fields.get("status"),
        priority=fields.get("priority"),
        severity=fields.get("severity"),
        owner=fields.get("owner"),
        detected_by=fields.get("detected-by"),
        description=strip_html(description_html),
        description_html=description_html,
        dev_comments=strip_html(dev_comments_html),
        dev_comments_html=dev_comments_html,
        created=fields.get("creation-time"),
        modified=fields.get("last-modified"),
        closed=fields.get("closing-date"),
        reproducible=fields.get("reproducible"),
        attachment=fields.get("attachment"),
        detected_in_rel=fields.get("detected-in-rel"),
        detected_in_rcyc=fields.get("detected-in-rcyc"),
        actual_fix_time=actual_fix_time,
        defect_type=fields.get("user-template-08"),
        application=fields.get("user-01"),
        workstream=fields.get("user-template-02"),
        module=fields.get("user-template-03"),
        target_date=fields.get("user-template-12"),
    )


def parse_alm_response(data: dict[str, Any]) -> list[Defect]:
    """Parse an ALM API response into a list of Defects.

    Args:
        data: Raw API response with 'entities' array.

    Returns:
        List of normalized Defect objects.
    """
    entities = data.get("entities", [])
    return [parse_alm_entity(entity) for entity in entities]
