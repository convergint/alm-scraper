"""Tests for SQL helper functions."""

from alm_scraper.constants import TERMINAL_STATUSES
from alm_scraper.sql_helpers import (
    age_bucket_case_sql,
    age_days_sql,
    age_expr_sql,
    build_in_clause,
    convergint_owner_filter,
    high_priority_filter,
    priority_sort_case_sql,
    terminal_status_filter,
    terminal_status_params,
)


class TestTerminalStatusFilter:
    """Tests for terminal_status_filter function."""

    def test_exclude_without_placeholders(self) -> None:
        result = terminal_status_filter(exclude=True, use_placeholders=False)
        assert "NOT IN" in result
        assert "LOWER(status)" in result
        assert "'closed'" in result
        assert "'rejected'" in result

    def test_include_without_placeholders(self) -> None:
        result = terminal_status_filter(exclude=False, use_placeholders=False)
        assert " IN (" in result
        assert "NOT IN" not in result
        assert "'closed'" in result

    def test_exclude_with_placeholders(self) -> None:
        result = terminal_status_filter(exclude=True, use_placeholders=True)
        assert "NOT IN" in result
        assert "?" in result
        assert "closed" not in result  # Should use ? not literal

    def test_params_match_terminal_statuses(self) -> None:
        params = terminal_status_params()
        assert len(params) == len(TERMINAL_STATUSES)
        assert "closed" in params
        assert "rejected" in params


class TestAgeBucketCaseSql:
    """Tests for age bucketing SQL generation."""

    def test_default_created_field(self) -> None:
        result = age_bucket_case_sql()
        assert "julianday('now')" in result
        assert "julianday(created)" in result
        assert "'0-7 days'" in result
        assert "'8-30 days'" in result
        assert "'31-90 days'" in result
        assert "'90+ days'" in result

    def test_custom_date_field(self) -> None:
        result = age_bucket_case_sql("modified")
        assert "julianday(modified)" in result
        assert "julianday(created)" not in result


class TestAgeDaysSql:
    """Tests for age in days SQL generation."""

    def test_returns_cast_expression(self) -> None:
        result = age_days_sql()
        assert "CAST(" in result
        assert "AS INTEGER" in result
        assert "julianday('now')" in result

    def test_custom_field(self) -> None:
        result = age_days_sql("closed")
        assert "julianday(closed)" in result


class TestAgeExprSql:
    """Tests for age expression SQL generation."""

    def test_returns_float_expression(self) -> None:
        result = age_expr_sql()
        assert "julianday('now')" in result
        assert "julianday(created)" in result
        assert "CAST" not in result  # Should be float, not cast


class TestPrioritySortCaseSql:
    """Tests for priority sorting SQL generation."""

    def test_includes_all_priorities(self) -> None:
        result = priority_sort_case_sql()
        assert "P1-Critical" in result
        assert "P2-High" in result
        assert "P3-Medium" in result
        assert "P4-Low" in result

    def test_correct_ordering(self) -> None:
        result = priority_sort_case_sql()
        # P1 should have lower sort value than P2
        p1_pos = result.find("P1-Critical")
        p2_pos = result.find("P2-High")
        assert p1_pos < p2_pos  # P1 comes first in CASE statement

    def test_has_else_clause(self) -> None:
        result = priority_sort_case_sql()
        assert "ELSE" in result

    def test_custom_field(self) -> None:
        result = priority_sort_case_sql("defect_priority")
        assert "CASE defect_priority" in result


class TestHighPriorityFilter:
    """Tests for high priority filter SQL generation."""

    def test_includes_p1_and_p2(self) -> None:
        result = high_priority_filter()
        assert "P1-Critical" in result
        assert "P2-High" in result
        assert "IN (" in result

    def test_excludes_lower_priorities(self) -> None:
        result = high_priority_filter()
        assert "P3-Medium" not in result
        assert "P4-Low" not in result

    def test_custom_field(self) -> None:
        result = high_priority_filter("p")
        assert "p IN" in result


class TestConvergintOwnerFilter:
    """Tests for Convergint owner filter SQL generation."""

    def test_uses_like_pattern(self) -> None:
        result = convergint_owner_filter()
        assert "LIKE" in result
        assert "convergint" in result
        assert "%" in result

    def test_custom_field(self) -> None:
        result = convergint_owner_filter("assigned_to")
        assert "assigned_to LIKE" in result


class TestBuildInClause:
    """Tests for IN clause builder."""

    def test_quoted_literals(self) -> None:
        result = build_in_clause(["a", "b", "c"], use_placeholders=False)
        assert result == "('a','b','c')"

    def test_placeholders(self) -> None:
        result = build_in_clause(["a", "b", "c"], use_placeholders=True)
        assert result == "(?,?,?)"

    def test_single_value(self) -> None:
        result = build_in_clause(["only"], use_placeholders=False)
        assert result == "('only')"

    def test_tuple_input(self) -> None:
        result = build_in_clause(("x", "y"), use_placeholders=False)
        assert result == "('x','y')"
