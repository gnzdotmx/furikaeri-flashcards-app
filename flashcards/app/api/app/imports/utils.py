import csv
import io
import logging
import unicodedata

logger = logging.getLogger(__name__)


def _import_defaults():
    try:
        from app.study_config import get_study_config
        imp = get_study_config().import_
        return imp.max_rows_default, imp.max_cell_chars_default
    except Exception:
        logger.debug("Using fallback import limits (study_config unavailable)")
        return 50_000, 20_000


def get_max_rows_default() -> int:
    return _import_defaults()[0]


def get_max_cell_chars_default() -> int:
    return _import_defaults()[1]


MAX_ROWS_DEFAULT = 50_000
MAX_CELL_CHARS_DEFAULT = 20_000


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = " ".join(s.split())
    return s.strip()


def normalize_notes_cell(value: str | None) -> str:
    """
    Normalize optional CSV notes: NFKC + strip ends only (preserves newlines within the cell).
    Used for the `notes` column; unlike norm_text, internal line breaks are kept.
    """
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value))
    return s.strip()


def decode_upload(data: bytes) -> io.StringIO:
    """Decode UTF-8 (with BOM) to StringIO for csv reader."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ValueError("CSV must be UTF-8 encoded") from e
    return io.StringIO(text, newline="")


def sniff_dialect(sample: str) -> csv.Dialect:
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(sample, delimiters=[",", "\t", ";"])
    except Exception:
        logger.debug("CSV sniff failed, using excel dialect")
        return csv.get_dialect("excel")


def validate_row_limits(cells, *, max_cell_chars: int) -> None:
    """Raise if any cell exceeds max_cell_chars. Cells can be values or list (DictReader extras)."""

    def check_one(value) -> None:
        if value is None:
            return
        s = str(value)
        if len(s) > max_cell_chars:
            raise ValueError(f"Cell too large ({len(s)} chars), max {max_cell_chars}")

    for cell in cells:
        if isinstance(cell, list):
            for v in cell:
                check_one(v)
        else:
            check_one(cell)

