"""Shared utilities for alm-scraper."""

import json
from pathlib import Path


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix if needed.

    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def strip_domain(owner: str) -> str:
    """Extract username from 'username_domain' format.

    Args:
        owner: Owner string, possibly with domain suffix.

    Returns:
        Username without domain.
    """
    return owner.split("_")[0] if "_" in owner else owner


def write_json(path: Path, data: dict | list, indent: int = 2) -> None:
    """Write data to JSON file with trailing newline.

    Args:
        path: Path to write to.
        data: Data to serialize.
        indent: JSON indentation level.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=indent)
        f.write("\n")
