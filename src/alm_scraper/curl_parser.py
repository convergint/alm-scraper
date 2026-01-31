"""Parse curl commands to extract URL, cookies, and headers."""

import re
import shlex
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class CurlConfig:
    """Parsed configuration from a curl command."""

    base_url: str
    domain: str
    project: str
    cookies: dict[str, str]


def parse_curl(curl_command: str) -> CurlConfig:
    """Parse a curl command and extract ALM configuration.

    Args:
        curl_command: A curl command string copied from browser DevTools.

    Returns:
        CurlConfig with base_url, domain, project, and cookies.

    Raises:
        ValueError: If the curl command is invalid or missing required parts.
    """
    # Normalize the command - handle multi-line and escape sequences
    normalized = curl_command.replace("\\\n", " ").replace("\n", " ")

    # Use shlex to properly parse the command with quotes
    try:
        tokens = shlex.split(normalized)
    except ValueError as e:
        raise ValueError(f"Failed to parse curl command: {e}") from e

    if not tokens or tokens[0] != "curl":
        raise ValueError("Command must start with 'curl'")

    url: str | None = None
    cookies: dict[str, str] = {}

    i = 1
    while i < len(tokens):
        token = tokens[i]

        if token in ("-b", "--cookie") and i + 1 < len(tokens):
            # Parse cookie string
            cookie_str = tokens[i + 1]
            cookies = parse_cookies(cookie_str)
            i += 2
        elif token in ("-H", "--header") and i + 1 < len(tokens):
            # Skip headers for now, we just need cookies
            i += 2
        elif token.startswith("-"):
            # Skip other flags
            # Some flags take arguments, some don't
            if token in ("-X", "--request", "--data-raw", "--data", "-d"):
                i += 2
            else:
                i += 1
        elif url is None:
            # First non-flag argument is the URL
            url = token
            i += 1
        else:
            i += 1

    if not url:
        raise ValueError("No URL found in curl command")

    if not cookies:
        raise ValueError("No cookies found in curl command (need -b flag)")

    # Parse the URL to extract ALM components
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/qcbin"

    # Extract domain and project from path
    # Pattern: /qcbin/rest/domains/{domain}/projects/{project}/...
    path_match = re.search(r"/domains/([^/]+)/projects/([^/]+)", parsed.path)
    if path_match:
        domain = path_match.group(1)
        project = path_match.group(2)
    else:
        raise ValueError(
            f"Could not extract domain/project from URL path: {parsed.path}\n"
            "Expected pattern: /domains/{{domain}}/projects/{{project}}/..."
        )

    return CurlConfig(
        base_url=base_url,
        domain=domain,
        project=project,
        cookies=cookies,
    )


def parse_cookies(cookie_str: str) -> dict[str, str]:
    """Parse a cookie string into a dictionary.

    Args:
        cookie_str: Cookie string in format "name1=value1; name2=value2"

    Returns:
        Dictionary mapping cookie names to values.
    """
    cookies: dict[str, str] = {}

    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue

        # Split on first = only (values can contain =)
        if "=" in part:
            name, value = part.split("=", 1)
            cookies[name.strip()] = value.strip()

    return cookies
