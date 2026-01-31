# RFC 007: Browser Cookie Extraction

**Status:** Draft  
**Author:** Claude  
**Created:** 2026-01-31

---

## Summary

Add automatic cookie extraction from the user's browser to eliminate the manual "copy cURL from DevTools" workflow when ALM session expires. This enables `alm config import-browser` to grab fresh cookies directly from Chrome/Firefox/Safari.

## Problem

Currently, when the ALM session expires (which happens frequently with Microsoft 365 SSO), users must:

1. Open browser, navigate to ALM
2. Open DevTools > Network tab
3. Find an API request, right-click > Copy as cURL
4. Run `alm config import-curl` and paste

This is tedious and error-prone. The session typically expires every few hours, making this a frequent annoyance.

**Current error when session expires:**

```bash
$ alm sync
Fetching defects from https://alm.deloitte.com/qcbin...
Error: HTTP 302
```

## Proposed Solution

Use `browser-cookie3` to extract cookies directly from the browser's cookie store. If the user is logged into ALM in their browser, we can grab fresh cookies without manual intervention.

**Supported browsers:** Arc, Chrome, Edge, Firefox. Safari requires Full Disk Access so we skip it with a warning.

### User Experience

**After:**

```bash
$ alm sync
Fetching defects from https://alm.deloitte.com/qcbin...
Error: Session expired - OAuth re-authentication required

To refresh your session:
  1. Log into ALM in your browser
  2. Copy a request as cURL from DevTools (Network tab)
  3. Run: alm config import-curl

Or try auto-extracting cookies from your browser:
  alm config import-browser

$ alm config import-browser
Searching for ALM cookies in browsers...
  Chrome: Found 12 cookies for alm.deloitte.com
  Firefox: Not found
  Safari: Not found

Imported config:
  base_url: https://alm.deloitte.com/qcbin
  domain:   CONVERGINT
  project:  Convergint_Transformation
  cookies:  12 cookies extracted

Saved to /Users/brian/.config/alm-scraper/config.json

$ alm sync
Fetching defects from https://alm.deloitte.com/qcbin...
  Page 1/2: 1000 defects
  Page 2/2: 1847 defects
Synced 1847 defects
```

### Commands

```bash
$ alm config import-browser --help
Usage: alm config import-browser [OPTIONS]

  Import cookies from your browser's cookie store.

  Searches Arc, Chrome, Edge, and Firefox for ALM cookies. Uses the first
  browser that has valid cookies.

Options:
  --browser [arc|chrome|edge|firefox]  Force a specific browser
  --help                               Show this message and exit.
```

## Error Handling

| Scenario                 | What User Sees                                           | Recovery Action                               |
| ------------------------ | -------------------------------------------------------- | --------------------------------------------- |
| No cookies found         | `Error: No ALM cookies found in any browser`             | Log into ALM in a supported browser           |
| Browser locked/encrypted | `Error: Could not read Chrome cookies (database locked)` | Close browser or use --browser to try another |
| Keychain access denied   | `Error: Could not decrypt cookies (Keychain access)`     | Grant Keychain access when prompted           |
| Safari attempted         | `Warning: Safari requires Full Disk Access, skipping`    | Use a different browser or grant FDA          |

### Example Error Messages

```bash
$ alm config import-browser
Searching for ALM cookies...
  Arc (Profile 1): no cookies
  Arc (Default): no cookies
  Chrome: no cookies
  Edge: no cookies
  Firefox: no cookies
  Safari: skipped (requires Full Disk Access)

Error: No ALM cookies found in any browser.

Log into ALM in Arc, Chrome, Edge, or Firefox:
  https://alm.deloitte.com/qcbin/webrunner/#/domains/CONVERGINT/projects/Convergint_Transformation/defects

Then run 'alm config import-browser' again.
```

## Safety & Edge Cases

### Browser Database Locking

Chrome/Arc locks its cookie database while running. Solution: copy the database to a temp file before reading.

### Keychain Access (macOS)

On first run, macOS will prompt for Keychain access to decrypt cookies. The user must:

1. Enter their password
2. Click "Always Allow" to avoid future prompts

If the prompt is missed or denied, the command will hang or fail.

### Cookie Expiration

Cookies extracted from browser may themselves be near expiration. This is fine - user will just need to refresh again soon.

### Multiple Profiles

Arc supports multiple profiles. We check "Profile 1" first, then "Default". Other Arc profiles are not checked (users with cookies in other profiles can use `import-curl` instead).

### Privacy/Security

- We only read cookies for the specific ALM domain
- Cookies are stored in the same config file as the cURL import
- No cookies are sent anywhere except to the ALM server

## Implementation Details

### Dependencies

Add as regular dependency:

```toml
dependencies = [
    ...
    "browser-cookie3>=0.19.1",
]
```

### Key Components

```python
# src/alm_scraper/browser.py
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
        browser: Force specific browser (arc/chrome/edge/firefox)
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
```

### CLI Integration

```python
# Hardcoded ALM config - same for all team members
ALM_BASE_URL = "https://alm.deloitte.com/qcbin"
ALM_DOMAIN = "CONVERGINT"
ALM_PROJECT = "Convergint_Transformation"
ALM_COOKIE_DOMAIN = "alm.deloitte.com"
ALM_LOGIN_URL = "https://alm.deloitte.com/qcbin/webrunner/#/domains/CONVERGINT/projects/Convergint_Transformation/defects"

@config.command("import-browser")
@click.option("--browser", type=click.Choice(["arc", "chrome", "edge", "firefox"]))
def import_browser(browser: str | None) -> None:
    """Import cookies from browser's cookie store."""
    from alm_scraper.browser import extract_cookies

    err.print("Searching for ALM cookies...")
    err.print("[dim]Note: First run may prompt for Keychain access.[/dim]")
    err.print()

    def on_status(name: str, status: str) -> None:
        err.print(f"  {name}: {status}")

    try:
        browser_name, cookies = extract_cookies(
            ALM_COOKIE_DOMAIN, browser=browser, on_status=on_status
        )
    except RuntimeError as e:
        err.print()
        err.print(f"[red]Error: {e}[/red]")
        err.print()
        err.print("Log into ALM in Arc, Chrome, Edge, or Firefox:")
        err.print(f"  {ALM_LOGIN_URL}")
        err.print()
        err.print("Then run 'alm config import-browser' again.")
        sys.exit(1)

    new_config = Config(
        base_url=ALM_BASE_URL,
        domain=ALM_DOMAIN,
        project=ALM_PROJECT,
        cookies=cookies,
    )

    path = save_config(new_config)

    err.print()
    err.print(f"[green]Imported {len(cookies)} cookies from {browser_name}[/green]")
    err.print(f"  base_url: {new_config.base_url}")
    err.print(f"  domain:   {new_config.domain}")
    err.print(f"  project:  {new_config.project}")
    err.print(f"  cookies:  {len(new_config.cookies)} cookies extracted")
    err.print()
    err.print(f"[green]Saved to {path}[/green]")
```

## Testing Strategy

### Unit Tests

```python
def test_extract_cookies_import_error():
    """Test helpful error when browser-cookie3 not installed."""
    # Mock import failure
    with pytest.raises(ImportError, match="browser-cookie3 not installed"):
        extract_cookies("example.com")

def test_extract_cookies_none_found():
    """Test error when no cookies found."""
    with pytest.raises(RuntimeError, match="No cookies found"):
        extract_cookies("nonexistent-domain.example.com")
```

### Manual Testing Checklist

- [ ] `alm config import-browser` works with Chrome logged in
- [ ] `alm config import-browser` works with Firefox logged in
- [ ] Clear error when no cookies found
- [ ] Clear error when browser-cookie3 not installed
- [ ] Clear error when no existing config
- [ ] `--browser chrome` flag works
- [ ] After import, `alm sync` succeeds

## Alternatives Considered

| Option                         | Pros                       | Cons                                    | Why Not                |
| ------------------------------ | -------------------------- | --------------------------------------- | ---------------------- |
| Status quo (cURL copy)         | Works reliably             | Tedious, frequent                       | User pain point        |
| Playwright/Selenium automation | Could fully automate login | Complex, fragile, may violate ToS       | Overkill               |
| Refresh token flow             | Standard OAuth approach    | ALM may not support, requires secrets   | Not available with SSO |
| Browser extension              | Could push cookies to CLI  | Requires extension install, maintenance | Too complex            |

## Out of Scope

| Item                       | Rationale                         |
| -------------------------- | --------------------------------- |
| Full OAuth automation      | Complex with SSO, may violate ToS |
| Multiple browser profiles  | Can add later if needed           |
| Keychain integration       | browser-cookie3 handles this      |
| Windows Credential Manager | macOS-focused for now             |

## Future Enhancements

1. **Auto-refresh on 302** - Automatically try browser import when session expires
2. **Cookie validity check** - Warn if cookies are near expiration
3. **Multiple profiles** - `--profile` flag for non-default browser profiles

## References

- [browser-cookie3 on PyPI](https://pypi.org/project/browser-cookie3/)
- [browser-cookie3 GitHub](https://github.com/borisbabic/browser_cookie3)
