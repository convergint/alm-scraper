"""Configuration management for alm-scraper."""

import json
from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    """ALM scraper configuration."""

    base_url: str
    domain: str
    project: str
    cookies: dict[str, str]


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    return Path.home() / ".config" / "alm-scraper"


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.json"


def load_config() -> Config | None:
    """Load configuration from file.

    Returns:
        Config if file exists and is valid, None otherwise.
    """
    path = get_config_path()
    if not path.exists():
        return None

    with path.open() as f:
        data = json.load(f)

    return Config.model_validate(data)


def save_config(config: Config) -> Path:
    """Save configuration to file.

    Args:
        config: Configuration to save.

    Returns:
        Path to the saved configuration file.
    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w") as f:
        json.dump(config.model_dump(), f, indent=2)
        f.write("\n")

    return path
