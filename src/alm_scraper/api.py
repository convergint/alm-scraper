"""ALM REST API client."""

import time
from collections.abc import Callable
from typing import Any

import httpx

from alm_scraper.config import Config


class ALMClient:
    """Client for ALM REST API."""

    def __init__(self, config: Config, debug: bool = False) -> None:
        """Initialize the client.

        Args:
            config: Configuration with base_url, domain, project, and cookies.
            debug: If True, print request/response details.
        """
        self.config = config
        self.base_url = config.base_url
        self.domain = config.domain
        self.project = config.project
        self.debug = debug

        # Build cookie header string
        cookie_str = "; ".join(f"{k}={v}" for k, v in config.cookies.items())

        self.headers = {
            "Accept": "application/json",
            "Cookie": cookie_str,
            "alm-client-type": "ALM Web Client UI",
        }

    def fetch_defects_page(self, page_size: int = 1000, start_index: int = 1) -> dict[str, Any]:
        """Fetch a page of defects.

        Args:
            page_size: Number of defects per page (max 1000).
            start_index: 1-indexed start position.

        Returns:
            Raw API response with 'entities' and 'TotalResults'.

        Raises:
            httpx.HTTPStatusError: On HTTP errors.
        """
        url = f"{self.base_url}/rest/domains/{self.domain}/projects/{self.project}/defects"

        params = {
            "page-size": str(page_size),
            "start-index": str(start_index),
            "order-by": "{id[asc];}",
        }

        if self.debug:
            import sys

            print(f"[DEBUG] GET {url}", file=sys.stderr)
            print(f"[DEBUG] Params: {params}", file=sys.stderr)
            print(f"[DEBUG] Headers: {self.headers}", file=sys.stderr)

        # Don't follow redirects - ALM redirects to login on auth failure
        response = httpx.get(
            url, headers=self.headers, params=params, timeout=60.0, follow_redirects=False
        )

        if self.debug:
            print(f"[DEBUG] Status: {response.status_code}", file=sys.stderr)
            print("[DEBUG] Response headers:", file=sys.stderr)
            for k, v in response.headers.items():
                print(f"[DEBUG]   {k}: {v}", file=sys.stderr)
            if response.status_code >= 400 or response.status_code in (301, 302, 303, 307, 308):
                # Show body for errors/redirects
                body = response.text[:1000]
                print("[DEBUG] Response body (first 1000 chars):", file=sys.stderr)
                print(f"[DEBUG]   {body}", file=sys.stderr)

        response.raise_for_status()

        return response.json()

    def fetch_all_defects(
        self,
        page_size: int = 500,
        delay: float = 1.0,
        on_page: Callable[[int, int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Fetch all defects with pagination.

        Args:
            page_size: Number of defects per page.
            delay: Seconds to wait between requests (be polite).
            on_page: Optional callback(page_num, total_pages, defects_so_far).

        Returns:
            Combined response with all entities and TotalResults.
        """
        all_entities: list[dict[str, Any]] = []
        start_index = 1
        total_results: int | None = None
        page_num = 0

        while True:
            page_num += 1
            data = self.fetch_defects_page(page_size=page_size, start_index=start_index)

            entities = data.get("entities", [])
            all_entities.extend(entities)

            if total_results is None:
                total_results = data.get("TotalResults", len(entities))

            total_pages = (total_results + page_size - 1) // page_size

            if on_page:
                on_page(page_num, total_pages, len(all_entities))

            # Check if we've fetched everything
            if len(entities) < page_size or len(all_entities) >= total_results:
                break

            # Be polite - wait between requests (but not before first request)
            start_index += page_size
            time.sleep(delay)

        return {
            "entities": all_entities,
            "TotalResults": total_results or len(all_entities),
        }
