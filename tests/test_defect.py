"""Tests for defect parsing."""

from alm_scraper.defect import parse_alm_entity, parse_alm_response, strip_html


class TestStripHtml:
    def test_strips_tags(self) -> None:
        html = "<html><body><p>Hello <b>world</b></p></body></html>"
        assert strip_html(html) == "Hello world"

    def test_normalizes_whitespace(self) -> None:
        html = "<p>Multiple   spaces\n\nand\nnewlines</p>"
        assert strip_html(html) == "Multiple spaces and newlines"

    def test_returns_none_for_none(self) -> None:
        assert strip_html(None) is None

    def test_returns_none_for_empty_after_strip(self) -> None:
        html = "<p>   </p>"
        assert strip_html(html) is None


class TestParseAlmEntity:
    def test_parses_basic_entity(self) -> None:
        entity = {
            "Fields": [
                {"Name": "id", "values": [{"value": "123"}]},
                {"Name": "name", "values": [{"value": "Test defect"}]},
                {"Name": "status", "values": [{"value": "Open"}]},
                {"Name": "priority", "values": [{"value": "P1-Critical"}]},
                {"Name": "owner", "values": [{"value": "jsmith"}]},
            ],
            "Type": "defect",
        }

        defect = parse_alm_entity(entity)

        assert defect.id == 123
        assert defect.name == "Test defect"
        assert defect.status == "Open"
        assert defect.priority == "P1-Critical"
        assert defect.owner == "jsmith"

    def test_handles_empty_values(self) -> None:
        entity = {
            "Fields": [
                {"Name": "id", "values": [{"value": "1"}]},
                {"Name": "name", "values": [{"value": "Test"}]},
                {"Name": "status", "values": []},
                {"Name": "priority", "values": [{}]},
            ],
        }

        defect = parse_alm_entity(entity)

        assert defect.id == 1
        assert defect.status is None
        assert defect.priority is None

    def test_strips_html_from_description(self) -> None:
        entity = {
            "Fields": [
                {"Name": "id", "values": [{"value": "1"}]},
                {"Name": "name", "values": [{"value": "Test"}]},
                {
                    "Name": "description",
                    "values": [{"value": "<p>This is a <b>test</b></p>"}],
                },
            ],
        }

        defect = parse_alm_entity(entity)

        assert defect.description == "This is a test"
        assert defect.description_html == "<p>This is a <b>test</b></p>"

    def test_parses_actual_fix_time_as_int(self) -> None:
        entity = {
            "Fields": [
                {"Name": "id", "values": [{"value": "1"}]},
                {"Name": "name", "values": [{"value": "Test"}]},
                {"Name": "actual-fix-time", "values": [{"value": "42"}]},
            ],
        }

        defect = parse_alm_entity(entity)
        assert defect.actual_fix_time == 42


class TestParseAlmResponse:
    def test_parses_multiple_entities(self) -> None:
        data = {
            "entities": [
                {
                    "Fields": [
                        {"Name": "id", "values": [{"value": "1"}]},
                        {"Name": "name", "values": [{"value": "First"}]},
                    ]
                },
                {
                    "Fields": [
                        {"Name": "id", "values": [{"value": "2"}]},
                        {"Name": "name", "values": [{"value": "Second"}]},
                    ]
                },
            ],
            "TotalResults": 2,
        }

        defects = parse_alm_response(data)

        assert len(defects) == 2
        assert defects[0].id == 1
        assert defects[0].name == "First"
        assert defects[1].id == 2
        assert defects[1].name == "Second"

    def test_handles_empty_response(self) -> None:
        data = {"entities": [], "TotalResults": 0}
        defects = parse_alm_response(data)
        assert defects == []
