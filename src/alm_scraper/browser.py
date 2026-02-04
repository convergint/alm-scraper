"""Browser cookie extraction for ALM authentication."""

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

import browser_cookie3


def _get_browser_configs() -> list[tuple[str, Callable, Path | None]]:
    """Get list of (name, loader_func, cookie_path) for each browser."""
    arc_base = Path.home() / "Library/Application Support/Arc/User Data"
    return [
        ("Arc (Profile 1)", browser_cookie3.arc, arc_base / "Profile 1" / "Cookies"),
        ("Arc (Default)", browser_cookie3.arc, arc_base / "Default" / "Cookies"),
        ("Brave", browser_cookie3.brave, None),
        ("Chrome", browser_cookie3.chrome, None),
        ("Edge", browser_cookie3.edge, None),
        ("Firefox", browser_cookie3.firefox, None),
    ]


def extract_cookies(
    domain: str,
    browser: str | None = None,
    on_status: Callable[[str, str], None] | None = None,
) -> tuple[str, dict[str, str]]:
    """Extract cookies for domain from available browsers.

    Args:
        domain: Domain to extract cookies for
        browser: Force specific browser (arc/brave/chrome/edge/firefox)
        on_status: Callback for status updates: (browser_name, status_msg)

    Returns:
        Tuple of (browser_name, cookies_dict)

    Raises:
        RuntimeError: No cookies found in any browser
    """
    browsers = _get_browser_configs()

    if browser:
        browsers = [(n, f, p) for n, f, p in browsers if browser.lower() in n.lower()]

    for name, loader, cookie_path in browsers:
        if cookie_path and not cookie_path.exists():
            if on_status:
                on_status(name, "not installed")
            continue

        try:
            if cookie_path:
                # Copy to temp to avoid locking
                with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                shutil.copy(cookie_path, tmp_path)
                try:
                    cj = loader(cookie_file=str(tmp_path), domain_name=domain)
                finally:
                    tmp_path.unlink(missing_ok=True)
            else:
                cj = loader(domain_name=domain)

            cookies = {c.name: c.value for c in cj}
            if cookies:
                if on_status:
                    on_status(name, f"found {len(cookies)} cookies")
                return name, cookies
            if on_status:
                on_status(name, "no cookies")

        except PermissionError:
            if on_status:
                on_status(name, "permission denied")
        except Exception as e:
            if on_status:
                on_status(name, f"error: {e}")

    if on_status:
        on_status("Safari", "skipped (requires Full Disk Access)")

    raise RuntimeError("No ALM cookies found in any browser")
