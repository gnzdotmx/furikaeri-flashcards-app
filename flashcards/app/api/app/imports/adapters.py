import csv
import json
import re
from dataclasses import dataclass

from .utils import MAX_CELL_CHARS_DEFAULT, MAX_ROWS_DEFAULT, normalize_notes_cell, norm_text, validate_row_limits


@dataclass(frozen=True)
class ImportItem:
    source_type: str
    level: str
    key: str
    fields: dict
    source_url: str | None = None


def _extract_examples(d: dict) -> list[str]:
    examples: list[str] = []
    for k, v in d.items():
        # DictReader puts "extra columns" on key None as a list[str].
        if k is None and isinstance(v, list):
            for extra in v:
                txt = str(extra).strip()
                if txt:
                    examples.append(txt)
            continue

        if not isinstance(k, str) or not k.startswith("example_"):
            continue
        if v is None:
            continue
        txt = str(v).strip()
        if txt:
            examples.append(txt)
    return examples


class GrammarCsvAdapter:
    """
    Grammar CSV (header-based):
      japanese_expression, english_meaning, grammar_structure,
      optional labels, optional notes, example_1, example_2, ...
    """

    REQUIRED = {"japanese_expression", "english_meaning"}

    def iter_items(
        self,
        *,
        level: str,
        reader: csv.DictReader,
        max_rows: int = MAX_ROWS_DEFAULT,
        max_cell_chars: int = MAX_CELL_CHARS_DEFAULT,
    ):
        headers = set(reader.fieldnames or [])
        missing = self.REQUIRED - headers
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for idx, row in enumerate(reader, start=1):
            if idx > max_rows:
                raise ValueError(f"Too many rows (>{max_rows})")
            validate_row_limits(row.values(), max_cell_chars=max_cell_chars)

            expr = norm_text(row.get("japanese_expression", ""))
            meaning = norm_text(row.get("english_meaning", ""))
            if not expr or not meaning:
                continue

            key = expr
            # Optional labels column (does not affect examples tail)
            raw_labels = (row.get("labels") or "").strip() if "labels" in headers else ""
            labels: list[str] = []
            if raw_labels:
                labels = [norm_text(p) for p in re.split(r"[;,]", raw_labels) if p.strip()]
            notes = normalize_notes_cell(row.get("notes")) if "notes" in headers else ""
            fields = {
                "japanese_expression": expr,
                "english_meaning": meaning,
                "grammar_structure": (row.get("grammar_structure") or "").strip(),
                "examples": _extract_examples(row),
                "labels": labels,
                "notes": notes,
            }
            yield ImportItem(source_type="grammar", level=level, key=key, fields=fields)


class KanjiCsvAdapter:
    """
    Kanji CSV (header-based):
      rank, kanji, onyomi, kunyomi, meaning,
      optional labels, optional notes, example_1, example_2, …
    source_url is not used; extra columns are collected as examples.
    """

    REQUIRED = {"kanji", "meaning"}

    def iter_items(
        self,
        *,
        level: str,
        reader: csv.DictReader,
        max_rows: int = MAX_ROWS_DEFAULT,
        max_cell_chars: int = MAX_CELL_CHARS_DEFAULT,
    ):
        headers = set(reader.fieldnames or [])
        missing = self.REQUIRED - headers
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for idx, row in enumerate(reader, start=1):
            if idx > max_rows:
                raise ValueError(f"Too many rows (>{max_rows})")
            validate_row_limits(row.values(), max_cell_chars=max_cell_chars)

            kanji = (row.get("kanji") or "").strip()
            meaning = norm_text(row.get("meaning", ""))
            if not kanji or not meaning:
                continue

            raw_labels = (row.get("labels") or "").strip() if "labels" in headers else ""
            labels: list[str] = []
            if raw_labels:
                labels = [norm_text(p) for p in re.split(r"[;,]", raw_labels) if p.strip()]
            notes = normalize_notes_cell(row.get("notes")) if "notes" in headers else ""
            fields = {
                "rank": (row.get("rank") or "").strip(),
                "kanji": kanji,
                "onyomi": (row.get("onyomi") or "").strip(),
                "kunyomi": (row.get("kunyomi") or "").strip(),
                "meaning": meaning,
                "labels": labels,
                "notes": notes,
                "examples": _extract_examples(row),
            }
            yield ImportItem(source_type="kanji", level=level, key=kanji, fields=fields)


class VocabularyCsvAdapter:
    """
    Vocabulary CSV (header-based, same example pattern as grammar):
      rank, word, reading_kana, reading_romaji, part_of_speech,
      optional labels, optional notes, meaning, example_1, example_2, ...
    After meaning, all columns are treated as examples: example_1, example_2, example_3, example_4, ...
    (same as grammar). Each example can be "jp\\nromaji\\nen". Extra columns beyond the header
    are also collected as examples.
    """

    REQUIRED = {"word", "meaning"}

    def iter_items(
        self,
        *,
        level: str,
        reader: csv.DictReader,
        max_rows: int = MAX_ROWS_DEFAULT,
        max_cell_chars: int = MAX_CELL_CHARS_DEFAULT,
    ):
        headers = set(reader.fieldnames or [])
        missing = self.REQUIRED - headers
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for idx, row in enumerate(reader, start=1):
            if idx > max_rows:
                raise ValueError(f"Too many rows (>{max_rows})")
            validate_row_limits(row.values(), max_cell_chars=max_cell_chars)

            # Normalize keys (strip) so "rank"/"word" are found even with BOM or spaces in header
            r = {(k.strip() if isinstance(k, str) else k): v for k, v in row.items()}

            word = (r.get("word") or "").strip()
            meaning = norm_text(r.get("meaning", ""))
            if not word or not meaning:
                continue

            reading_kana = (r.get("reading_kana") or "").strip()
            # If CSV column order is word,rank,... instead of rank,word,..., the "word" cell can
            # contain the rank (e.g. "2" or "9"). Swap so we never show rank on the card.
            rank_val = (r.get("rank") or "").strip()
            if rank_val and word.isdigit() and not rank_val.isdigit():
                word, _ = rank_val, word
            # Never emit a card whose word is a number (rank); skip row if we couldn't fix it
            if not word or word.isdigit():
                continue
            part_of_speech = (r.get("part_of_speech") or "").strip()
            # Don't use rank as part_of_speech (e.g. column shift); clear if purely numeric
            if part_of_speech.isdigit():
                part_of_speech = ""
            # Optional labels column: sits between part_of_speech and meaning in header
            raw_labels = (r.get("labels") or "").strip() if "labels" in headers else ""
            labels: list[str] = []
            if raw_labels:
                labels = [norm_text(p) for p in re.split(r"[;,]", raw_labels) if p.strip()]
            notes = normalize_notes_cell(r.get("notes")) if "notes" in headers else ""
            key = "|".join([word, reading_kana, meaning])
            # Never include "rank" in fields so it never appears on flashcards.
            # Optional example_1, example_2, ... (same as grammar/kanji) so examples display in GUI.
            fields = {
                "word": word,
                "reading_kana": reading_kana,
                "reading_romaji": (r.get("reading_romaji") or "").strip(),
                "part_of_speech": part_of_speech,
                "meaning": meaning,
                "labels": labels,
                "notes": notes,
                "examples": _extract_examples(r),
            }
            yield ImportItem(source_type="vocabulary", level=level, key=key, fields=fields)


class GenericVocabularyCsvAdapter:
    """
    Generic vocabulary CSV (positional columns). First row is always treated as header.
      A = English (meaning)
      B = Kanji
      C = Hiragana
      D = example1, E = example2, ... (optional example columns)
    """

    def iter_items(
        self,
        *,
        level: str,
        rows: list[list[str]],
        max_rows: int = MAX_ROWS_DEFAULT,
        max_cell_chars: int = MAX_CELL_CHARS_DEFAULT,
    ):
        for idx, row in enumerate(rows, start=1):
            if idx > max_rows:
                raise ValueError(f"Too many rows (>{max_rows})")
            validate_row_limits([c or "" for c in row], max_cell_chars=max_cell_chars)
            if len(row) < 3:
                continue

            english = norm_text(row[0])
            kanji = norm_text(row[1])
            hira = norm_text(row[2])
            if not english or (not kanji and not hira):
                continue

            examples = [c.strip() for c in row[3:] if c and c.strip()]
            key = f"{english}|{kanji}|{hira}"
            fields = {
                "english_word": english,
                "kanji_word": kanji,
                "hiragana_word": hira,
                "examples": examples,
            }
            yield ImportItem(source_type="vocabulary", level=level, key=key, fields=fields)


class GenericVocabularyCsvAdapterWordReadingMeaning:
    """
    Generic vocabulary CSV (positional). First row is always treated as header.
      A: kanji_word (or kana if no kanji)
      B: hiragana_word (reading)
      C: english_word (meaning)
      D...: examples (optional)
    Use when your CSV has columns: word, reading, meaning.
    """

    def iter_items(
        self,
        *,
        level: str,
        rows: list[list[str]],
        max_rows: int = MAX_ROWS_DEFAULT,
        max_cell_chars: int = MAX_CELL_CHARS_DEFAULT,
    ):
        for idx, row in enumerate(rows, start=1):
            if idx > max_rows:
                raise ValueError(f"Too many rows (>{max_rows})")
            validate_row_limits([c or "" for c in row], max_cell_chars=max_cell_chars)
            if len(row) < 3:
                continue

            word = norm_text(row[0])
            reading = norm_text(row[1])
            meaning = norm_text(row[2])
            if not meaning or (not word and not reading):
                continue

            if not word:
                word = reading
            examples = [c.strip() for c in row[3:] if c and c.strip()]
            key = f"{word}|{reading}|{meaning}"
            fields = {
                "english_word": meaning,
                "kanji_word": word,
                "hiragana_word": reading,
                "meaning": meaning,
                "examples": examples,
            }
            yield ImportItem(source_type="vocabulary", level=level, key=key, fields=fields)


def encode_fields_json(fields: dict) -> str:
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


class GenericKanjiCsvAdapter:
    """
    Generic kanji CSV (positional):
      A: kanji
      B: meaning
      C: onyomi (optional)
      D: kunyomi (optional)
      E...: examples
    """

    def iter_items(
        self,
        *,
        level: str,
        rows: list[list[str]],
        max_rows: int = MAX_ROWS_DEFAULT,
        max_cell_chars: int = MAX_CELL_CHARS_DEFAULT,
    ):
        for idx, row in enumerate(rows, start=1):
            if idx > max_rows:
                raise ValueError(f"Too many rows (>{max_rows})")
            validate_row_limits([c or "" for c in row], max_cell_chars=max_cell_chars)
            if len(row) < 2:
                continue
            kanji = (row[0] or "").strip()
            meaning = norm_text(row[1])
            if not kanji or not meaning:
                continue
            onyomi = row[2].strip() if len(row) >= 3 and row[2] else ""
            kunyomi = row[3].strip() if len(row) >= 4 and row[3] else ""
            examples = [c.strip() for c in row[4:] if c and c.strip()] if len(row) >= 5 else []
            fields = {
                "kanji": kanji,
                "meaning": meaning,
                "onyomi": onyomi,
                "kunyomi": kunyomi,
                "examples": examples,
            }
            yield ImportItem(source_type="kanji", level=level, key=kanji, fields=fields)

