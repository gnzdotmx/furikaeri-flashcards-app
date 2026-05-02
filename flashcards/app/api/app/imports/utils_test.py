"""Tests for app.imports.utils."""

import pytest

from app.imports.utils import (
    MAX_CELL_CHARS_DEFAULT,
    MAX_ROWS_DEFAULT,
    decode_upload,
    get_max_cell_chars_default,
    get_max_rows_default,
    normalize_notes_cell,
    norm_text,
    sniff_dialect,
    validate_row_limits,
)


def test_constants() -> None:
    assert MAX_ROWS_DEFAULT == 50_000
    assert MAX_CELL_CHARS_DEFAULT == 20_000


def test_get_import_defaults_from_config() -> None:
    """get_max_rows_default and get_max_cell_chars_default return config or fallback."""
    assert get_max_rows_default() >= 1000
    assert get_max_rows_default() <= 1_000_000
    assert get_max_cell_chars_default() >= 1000
    assert get_max_cell_chars_default() <= 100_000
    # With default config they match the constants
    from app.study_config import get_study_config
    cfg = get_study_config()
    assert get_max_rows_default() == cfg.import_.max_rows_default
    assert get_max_cell_chars_default() == cfg.import_.max_cell_chars_default


def test_norm_text_none_or_empty() -> None:
    assert norm_text(None) == ""
    assert norm_text("") == ""
    assert norm_text("   ") == ""


def test_norm_text_collapses_whitespace() -> None:
    assert norm_text("  a  b  c  ") == "a b c"
    assert norm_text("a\t\nb") == "a b"


def test_normalize_notes_cell_preserves_newlines() -> None:
    assert normalize_notes_cell("  line1\nline2  ") == "line1\nline2"
    assert normalize_notes_cell(None) == ""


def test_normalize_notes_cell_nfkc() -> None:
    assert normalize_notes_cell("ｶﾞ") == "ガ"


def test_norm_text_nfkc() -> None:
    # NFKC normalizes halfwidth katakana to fullwidth
    assert norm_text("ｶﾞ") == "ガ"
    # Full-width space collapses like other whitespace
    assert " " in norm_text("a　b") and norm_text("a　b").strip() == "a b"


def test_decode_upload_utf8() -> None:
    data = "hello,world\n1,2".encode("utf-8")
    buf = decode_upload(data)
    assert buf.read() == "hello,world\n1,2"


def test_decode_upload_utf8_bom() -> None:
    # utf-8-sig encoding adds BOM; decode_upload strips it
    data = "a,b\n".encode("utf-8-sig")
    buf = decode_upload(data)
    assert buf.read() == "a,b\n"


def test_decode_upload_invalid_encoding_raises() -> None:
    data = b"\xff\xfe"
    with pytest.raises(ValueError, match="CSV must be UTF-8 encoded"):
        decode_upload(data)


def test_decode_upload_returns_stringio_newline_empty() -> None:
    data = "x,y\n".encode("utf-8")
    buf = decode_upload(data)
    assert buf.getvalue() == "x,y\n"


def test_sniff_dialect_comma() -> None:
    sample = "a,b,c\n1,2,3"
    d = sniff_dialect(sample)
    assert d.delimiter == ","


def test_sniff_dialect_tab() -> None:
    sample = "a\tb\tc\n1\t2\t3"
    d = sniff_dialect(sample)
    assert d.delimiter == "\t"


def test_sniff_dialect_fallback_on_ambiguous() -> None:
    # Sniffer might fail on very short/ambiguous sample; we get excel dialect
    d = sniff_dialect("x")
    assert hasattr(d, "delimiter")


def test_validate_row_limits_ok() -> None:
    validate_row_limits(["a", "bb", "ccc"], max_cell_chars=10)
    validate_row_limits([None, ""], max_cell_chars=5)


def test_validate_row_limits_cell_too_large_raises() -> None:
    with pytest.raises(ValueError, match="Cell too large"):
        validate_row_limits(["short", "x" * 25], max_cell_chars=20)


def test_validate_row_limits_nested_list() -> None:
    # DictReader extra columns under key None as list
    validate_row_limits([["a", "b"]], max_cell_chars=10)
    with pytest.raises(ValueError, match="Cell too large"):
        validate_row_limits([["x" * 25]], max_cell_chars=20)
