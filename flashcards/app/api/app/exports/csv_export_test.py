"""Tests for app.exports.csv_export."""

from app.exports.csv_export import sanitize_csv_cell, write_csv


class TestSanitizeCsvCell:
    def test_none_returns_empty(self) -> None:
        assert sanitize_csv_cell(None) == ""

    def test_plain_string_unchanged(self) -> None:
        assert sanitize_csv_cell("hello") == "hello"
        assert sanitize_csv_cell("123") == "123"
        assert sanitize_csv_cell("") == ""

    def test_formula_starts_with_equals_prefixed(self) -> None:
        assert sanitize_csv_cell("=1+1") == "'=1+1"
        assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"

    def test_formula_starts_with_plus_prefixed(self) -> None:
        assert sanitize_csv_cell("+1") == "'+1"

    def test_formula_starts_with_minus_prefixed(self) -> None:
        assert sanitize_csv_cell("-1") == "'-1"

    def test_formula_starts_with_at_prefixed(self) -> None:
        assert sanitize_csv_cell("@REF") == "'@REF"

    def test_leading_whitespace_then_formula_prefixed(self) -> None:
        assert sanitize_csv_cell("  =1+1") == "'  =1+1"
        assert sanitize_csv_cell("\t+1") == "'\t+1"

    def test_equals_not_at_start_unchanged(self) -> None:
        assert sanitize_csv_cell("x=1") == "x=1"
        assert sanitize_csv_cell("a+b") == "a+b"

    def test_non_string_coerced_to_str(self) -> None:
        assert sanitize_csv_cell(42) == "42"
        assert sanitize_csv_cell(3.14) == "3.14"
        assert sanitize_csv_cell(0) == "0"


class TestWriteCsv:
    def test_empty_rows_header_only(self) -> None:
        out = write_csv([], ["a", "b"])
        lines = out.strip().splitlines()
        assert len(lines) == 1
        assert lines[0] == "a,b"

    def test_one_row(self) -> None:
        out = write_csv([{"a": "1", "b": "2"}], ["a", "b"])
        lines = out.strip().splitlines()
        assert lines[0] == "a,b"
        assert lines[1] == "1,2"

    def test_sanitization_applied(self) -> None:
        out = write_csv([{"x": "=1+1", "y": "safe"}], ["x", "y"])
        lines = out.strip().splitlines()
        assert lines[1] == "'=1+1,safe"

    def test_missing_keys_become_empty(self) -> None:
        out = write_csv([{"a": "only"}], ["a", "b"])
        lines = out.strip().splitlines()
        assert lines[1] == "only,"

    def test_extra_keys_ignored(self) -> None:
        out = write_csv([{"a": "1", "b": "2", "extra": "ignored"}], ["a", "b"])
        lines = out.strip().splitlines()
        assert lines[1] == "1,2"

    def test_multiple_rows(self) -> None:
        out = write_csv(
            [{"k": "1"}, {"k": "2"}, {"k": "3"}],
            ["k"],
        )
        lines = out.strip().splitlines()
        assert lines == ["k", "1", "2", "3"]

    def test_values_with_comma_quoted(self) -> None:
        out = write_csv([{"a": "x,y", "b": "z"}], ["a", "b"])
        lines = out.strip().splitlines()
        assert lines[0] == "a,b"
        assert "x,y" in out
        assert "z" in out

    def test_formula_in_middle_of_value_unchanged(self) -> None:
        out = write_csv([{"x": "text=1+1"}], ["x"])
        lines = out.strip().splitlines()
        assert lines[1] == "text=1+1"
