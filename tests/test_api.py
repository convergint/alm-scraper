"""Tests for API helper functions."""

import pytest
from fastapi.testclient import TestClient

from alm_scraper.ui.api import app, clean_html, format_dev_comments


class TestSearchEndpoint:
    """Tests for the /api/defects search functionality."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app)

    def test_search_returns_results(self, client: TestClient) -> None:
        """Search with a query should return matching defects."""
        response = client.get("/api/defects", params={"q": "oracle"})
        assert response.status_code == 200
        data = response.json()
        assert "defects" in data
        assert "total" in data
        assert data["total"] > 0
        # Check that results contain the search term
        assert any("oracle" in d["name"].lower() for d in data["defects"])

    def test_search_with_empty_query_returns_all(self, client: TestClient) -> None:
        """Empty search query should return all defects (paginated)."""
        response = client.get("/api/defects", params={"q": ""})
        assert response.status_code == 200
        data = response.json()
        assert "defects" in data
        assert data["total"] > 0

    def test_search_pagination(self, client: TestClient) -> None:
        """Search results should be paginated correctly."""
        response = client.get("/api/defects", params={"q": "oracle", "page": 1, "limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert len(data["defects"]) <= 5
        assert "pages" in data

    def test_search_with_status_filter(self, client: TestClient) -> None:
        """Search should work with additional status filter."""
        response = client.get("/api/defects", params={"q": "oracle", "status": "closed"})
        assert response.status_code == 200
        data = response.json()
        # All returned defects should have closed status
        for d in data["defects"]:
            assert d["status"].lower() == "closed"

    def test_search_no_results(self, client: TestClient) -> None:
        """Search for non-existent term should return empty results."""
        response = client.get("/api/defects", params={"q": "xyznonexistent123"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["defects"] == []

    def test_search_with_terminal_filter(self, client: TestClient) -> None:
        """Search should work with !terminal status filter (active defects only)."""
        # First verify search without filter returns results including some active
        response_all = client.get("/api/defects", params={"q": "oracle"})
        assert response_all.status_code == 200
        data_all = response_all.json()
        assert data_all["total"] > 0, "Search should return results without filter"

        # Verify there are some non-terminal results in the full search
        terminal_statuses = ("closed", "rejected", "duplicate", "deferred")
        active_count = sum(
            1
            for d in data_all["defects"]
            if d["status"] and d["status"].lower() not in terminal_statuses
        )
        assert active_count > 0, "Test requires some active defects in search results"

        # Now search with !terminal filter
        response = client.get("/api/defects", params={"q": "oracle", "status": "!terminal"})
        assert response.status_code == 200
        data = response.json()

        # Should return results (not empty)
        assert data["total"] > 0, "Search with !terminal should return active defects"

        # Should return only active (non-terminal) defects
        for d in data["defects"]:
            assert d["status"].lower() not in terminal_statuses, (
                f"Defect {d['id']} has terminal status {d['status']}"
            )

    def test_search_with_not_closed_filter(self, client: TestClient) -> None:
        """Search should work with !closed status filter."""
        response = client.get("/api/defects", params={"q": "oracle", "status": "!closed"})
        assert response.status_code == 200
        data = response.json()

        # Should return only non-closed defects
        for d in data["defects"]:
            assert d["status"].lower() != "closed", f"Defect {d['id']} has closed status"

    def test_filter_by_workstream(self, client: TestClient) -> None:
        """Filter by workstream should return matching defects."""
        response = client.get("/api/defects", params={"workstream": "CPQ"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0, "Should find defects with CPQ workstream"
        # All results should have CPQ in workstream (partial match)
        for d in data["defects"]:
            assert d["workstream"] and "cpq" in d["workstream"].lower(), (
                f"Defect {d['id']} workstream {d['workstream']} doesn't match CPQ"
            )

    def test_filter_by_defect_type(self, client: TestClient) -> None:
        """Filter by defect_type should return matching defects."""
        response = client.get("/api/defects", params={"defect_type": "Configuration"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0, "Should find defects with Configuration type"
        # All results should have Configuration in defect_type (partial match)
        for d in data["defects"]:
            assert d["defect_type"] and "configuration" in d["defect_type"].lower(), (
                f"Defect {d['id']} type {d['defect_type']} doesn't match Configuration"
            )

    def test_filter_workstream_with_search(self, client: TestClient) -> None:
        """Workstream filter should work combined with search."""
        response = client.get("/api/defects", params={"q": "error", "workstream": "CPQ"})
        assert response.status_code == 200
        data = response.json()
        # All results should match both criteria
        for d in data["defects"]:
            assert d["workstream"] and "cpq" in d["workstream"].lower()

    def test_filter_defect_type_with_search(self, client: TestClient) -> None:
        """Defect type filter should work combined with search."""
        response = client.get("/api/defects", params={"q": "error", "defect_type": "Code"})
        assert response.status_code == 200
        data = response.json()
        # All results should match both criteria
        for d in data["defects"]:
            assert d["defect_type"] and "code" in d["defect_type"].lower()


class TestCleanHtml:
    """Tests for the clean_html function."""

    def test_returns_none_for_none(self) -> None:
        assert clean_html(None) is None

    def test_returns_empty_for_empty_string(self) -> None:
        # Empty string input returns empty string (falsy but not None)
        assert clean_html("") == ""

    def test_converts_plain_text_newlines_to_br(self) -> None:
        """Plain text without HTML tags should have newlines converted to <br>."""
        result = clean_html("Line 1\nLine 2\nLine 3")
        assert "<br>" in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_preserves_structure_from_html(self) -> None:
        """HTML with divs and br tags should preserve structure."""
        html = """<html><body>
<div>Hi Fran<br /></div>
<div>Second paragraph<br /></div>
</body></html>"""
        result = clean_html(html)
        # Should have div structure preserved
        assert "<div>" in result or "<br>" in result
        assert "Hi Fran" in result
        assert "Second paragraph" in result

    def test_strips_inline_styles(self) -> None:
        """Inline styles should be removed."""
        html = '<div style="color:red;font-size:12px">Text</div>'
        result = clean_html(html)
        assert "style=" not in result
        assert "Text" in result

    def test_strips_font_tags(self) -> None:
        """Font tags should be unwrapped (content preserved)."""
        html = '<font face="Arial" color="#000080">Text content</font>'
        result = clean_html(html)
        assert "<font" not in result
        assert "Text content" in result

    def test_strips_span_tags(self) -> None:
        """Span tags should be unwrapped (content preserved)."""
        html = '<span dir="ltr" style="font-size:8pt">Text content</span>'
        result = clean_html(html)
        assert "<span" not in result
        assert "Text content" in result

    def test_preserves_links(self) -> None:
        """Links should be preserved."""
        html = '<a href="https://example.com">Click here</a>'
        result = clean_html(html)
        assert "href=" in result
        assert "Click here" in result

    def test_preserves_tables(self) -> None:
        """Tables should be preserved."""
        html = "<table><tr><td>Cell 1</td><td>Cell 2</td></tr></table>"
        result = clean_html(html)
        assert "<table>" in result
        assert "Cell 1" in result


class TestFormatDevComments:
    """Tests for the format_dev_comments function."""

    def test_returns_none_for_none(self) -> None:
        assert format_dev_comments(None) is None

    def test_returns_empty_for_empty_string(self) -> None:
        # Empty string input returns empty string (falsy but not None)
        assert format_dev_comments("") == ""

    def test_simple_text_converts_newlines(self) -> None:
        """Plain text without headers should just convert newlines to br tags."""
        result = format_dev_comments("Line 1\nLine 2")
        assert "<br>" in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_parses_author_date_header(self) -> None:
        """Comments with author, date: format should be parsed."""
        text = "jsmith, 12/25/2025: This is my comment"
        result = format_dev_comments(text)
        assert "comment-author" in result
        assert "comment-date" in result
        assert "jsmith" in result
        assert "This is my comment" in result

    def test_parses_author_with_angle_brackets(self) -> None:
        """Author names with <username> format should be parsed."""
        text = "John Smith <jsmith>, 01-15-2026[dd-MM-yyyy]: Comment text"
        result = format_dev_comments(text)
        assert "comment-author" in result
        assert "John Smith" in result
        assert "Comment text" in result

    def test_parses_multiple_comments(self) -> None:
        """Multiple comments separated by _______ should each get formatted."""
        text = """jsmith, 12/25/2025: First comment
_______________________________
jdoe, 12/26/2025: Second comment"""
        result = format_dev_comments(text)
        assert result.count("comment-block") == 2
        assert "First comment" in result
        assert "Second comment" in result

    def test_date_formats_normalized_to_iso(self) -> None:
        """Various date formats should be normalized to ISO format."""
        # MM/DD/YYYY format
        text1 = "user, 12/25/2025: Comment"
        result1 = format_dev_comments(text1)
        assert "2025-12-25" in result1

        # DD-MM-YYYY format with hint
        text2 = "user, 25-12-2025[dd-MM-yyyy]: Comment"
        result2 = format_dev_comments(text2)
        assert "2025-12-25" in result2

    def test_escapes_html_in_comment_body(self) -> None:
        """HTML in comment body should be escaped to prevent XSS."""
        text = "user, 12/25/2025: <script>alert('xss')</script>"
        result = format_dev_comments(text)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_preserves_newlines_in_comment_body(self) -> None:
        """Newlines within a comment should become <br> tags."""
        text = "user, 12/25/2025: Line 1\nLine 2\nLine 3"
        result = format_dev_comments(text)
        assert "<br>" in result


class TestCleanHtmlRealWorld:
    """Test clean_html with real-world ALM HTML content."""

    def test_alm_description_html(self) -> None:
        """Test with actual ALM description HTML structure."""
        html = """<html><body>
<div align="left" style="min-height:9pt">
<font face="Arial"><span dir="ltr" style="font-size:8pt">Hi Fran<br /></span></font>
</div>
<div align="left" style="min-height:9pt">
<font face="Arial"><span style="font-size:8pt">We've identified issues.<br /></span></font>
</div>
</body></html>"""
        result = clean_html(html)

        # Should have readable content
        assert "Hi Fran" in result
        assert "identified issues" in result

        # Should NOT have style attributes
        assert "style=" not in result

        # Should NOT have font/span tags
        assert "<font" not in result
        assert "<span" not in result

        # Should have some structure (br or div)
        assert "<br>" in result or "<div>" in result
