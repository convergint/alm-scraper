"""Tests for curl command parsing."""

import pytest

from alm_scraper.curl_parser import parse_cookies, parse_curl


class TestParseCookies:
    def test_simple_cookies(self) -> None:
        result = parse_cookies("foo=bar; baz=qux")
        assert result == {"foo": "bar", "baz": "qux"}

    def test_cookie_with_equals_in_value(self) -> None:
        result = parse_cookies("token=abc=def=ghi")
        assert result == {"token": "abc=def=ghi"}

    def test_empty_string(self) -> None:
        result = parse_cookies("")
        assert result == {}

    def test_whitespace_handling(self) -> None:
        result = parse_cookies("  foo = bar ;  baz=qux  ")
        assert result == {"foo": "bar", "baz": "qux"}


class TestParseCurl:
    def test_basic_curl(self) -> None:
        url = "https://alm.example.com/qcbin/rest/domains/MYDOMAIN/projects/MyProject/defects"
        curl = f"curl '{url}' -b 'session=abc123'"
        result = parse_curl(curl)

        assert result.base_url == "https://alm.example.com/qcbin"
        assert result.domain == "MYDOMAIN"
        assert result.project == "MyProject"
        assert result.cookies == {"session": "abc123"}

    def test_multiline_curl(self) -> None:
        url = "https://alm.example.com/qcbin/rest/domains/MYDOMAIN/projects/MyProject/defects"
        curl = f"""curl '{url}' \\
  -H 'accept: application/json' \\
  -b 'session=abc123; token=xyz'"""
        result = parse_curl(curl)

        assert result.domain == "MYDOMAIN"
        assert result.project == "MyProject"
        assert result.cookies == {"session": "abc123", "token": "xyz"}

    def test_real_alm_curl(self) -> None:
        """Test with a realistic ALM curl command."""
        base = "https://alm.deloitte.com/qcbin/rest/domains/CONVERGINT"
        url = f"{base}/projects/Convergint_Transformation/defects?page-size=1000"
        cookies = (
            "JSESSIONID=node123; access_token=eHwABC123; "
            "QCSession-YWxtIHdlYg==xyz; ALM_USER=hash123; XSRF-TOKEN=csrf456"
        )
        curl = f"""curl '{url}' \\
  -H 'accept: application/json' \\
  -H 'alm-client-type: ALM Web Client UI' \\
  -b '{cookies}'"""

        result = parse_curl(curl)

        assert result.base_url == "https://alm.deloitte.com/qcbin"
        assert result.domain == "CONVERGINT"
        assert result.project == "Convergint_Transformation"
        assert result.cookies["JSESSIONID"] == "node123"
        assert result.cookies["access_token"] == "eHwABC123"
        assert "QCSession-YWxtIHdlYg" in result.cookies
        assert result.cookies["ALM_USER"] == "hash123"
        assert result.cookies["XSRF-TOKEN"] == "csrf456"

    def test_missing_url_raises(self) -> None:
        with pytest.raises(ValueError, match="No URL found"):
            parse_curl("curl -b 'foo=bar'")

    def test_missing_cookies_raises(self) -> None:
        with pytest.raises(ValueError, match="No cookies found"):
            parse_curl("curl 'https://example.com/qcbin/rest/domains/D/projects/P/x'")

    def test_invalid_url_path_raises(self) -> None:
        with pytest.raises(ValueError, match="Could not extract domain/project"):
            parse_curl("curl 'https://example.com/other/path' -b 'foo=bar'")

    def test_not_curl_raises(self) -> None:
        with pytest.raises(ValueError, match="must start with 'curl'"):
            parse_curl("wget https://example.com")
