"""
Export deck cards in the same CSV format as import (vocabulary, grammar, kanji).
One row per note; format matches the corresponding import adapter so round-trip is lossless.

Storage (SQLite):
- Deck CSV column `notes` (shown as "Deck note" when studying): `notes.fields_json` -> key "notes",
  and a copy on each generated card's `back_template` JSON -> "notes".
- Per-card "My note" (study UI): `card_study_notes` (user_id, card_id, body). When export_user_id
  is set, distinct My note bodies for cards of that note are appended into the exported `notes` cell
  so backup/round-trip does not lose personal text.
"""

import json
from typing import Any

from ..repositories.notes import NoteRepository
from .csv_export import sanitize_csv_cell, write_csv


def _notes_cell_for_export(fields: dict[str, Any], back_fallback: dict[str, Any] | None) -> str:
    """Deck CSV `notes` from note fields, or from card back_template if fields were cleared by an old merge."""
    for src in (fields, back_fallback):
        if not src:
            continue
        v = src.get("notes")
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _study_notes_by_card_id(conn: Any, user_id: str, deck_id: str) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT csn.card_id AS card_id, csn.body AS body
        FROM card_study_notes AS csn
        INNER JOIN cards AS c ON c.id = csn.card_id
        WHERE csn.user_id = ? AND c.deck_id = ?;
        """,
        (user_id, deck_id),
    ).fetchall()
    return {str(r["card_id"]): str(r["body"]) for r in rows}


def _study_bodies_for_note(study_by_card: dict[str, str], card_rows: list[dict[str, Any]], note_id: str) -> list[str]:
    bodies: list[str] = []
    seen: set[str] = set()
    for c in card_rows:
        if (c.get("note_id") or "") != note_id:
            continue
        cid = c.get("id")
        if not cid:
            continue
        body = study_by_card.get(str(cid))
        if not body:
            continue
        t = str(body).strip()
        if t and t not in seen:
            seen.add(t)
            bodies.append(t)
    return bodies


def _compose_csv_notes_cell(deck_notes: str, study_bodies: list[str]) -> str:
    """Single CSV `notes` field: imported deck note plus distinct per-card study notes for this note."""
    parts: list[str] = []
    d = (deck_notes or "").strip()
    if d:
        parts.append(d)
    seen = set(parts)
    for raw in study_bodies:
        s = str(raw or "").strip()
        if s and s not in seen:
            seen.add(s)
            parts.append(s)
    return "\n\n".join(parts)


def _labels_cell_from_fields(fields: dict[str, Any]) -> str:
    labels = fields.get("labels")
    if isinstance(labels, list):
        parts = [str(x).strip() for x in labels if x is not None and str(x).strip()]
        return ";".join(parts)
    if labels:
        return str(labels).strip()
    return ""


# Vocabulary: rank, word, reading_kana, reading_romaji, part_of_speech, labels, notes, meaning, example_1..N
VOCAB_FIELDNAMES = [
    "rank",
    "word",
    "reading_kana",
    "reading_romaji",
    "part_of_speech",
    "labels",
    "notes",
    "meaning",
    "example_1",
    "example_2",
    "example_3",
    "example_4",
    "example_5",
]

# Grammar: japanese_expression, english_meaning, grammar_structure, labels, notes, example_1..N
GRAMMAR_FIELDNAMES = [
    "japanese_expression",
    "english_meaning",
    "grammar_structure",
    "labels",
    "notes",
    "example_1",
    "example_2",
    "example_3",
    "example_4",
    "example_5",
]

# Kanji: rank, kanji, onyomi, kunyomi, meaning, labels, notes, example_1..N
KANJI_FIELDNAMES = [
    "rank",
    "kanji",
    "onyomi",
    "kunyomi",
    "meaning",
    "labels",
    "notes",
    "example_1",
    "example_2",
    "example_3",
    "example_4",
    "example_5",
]

# Legacy/raw format when we cannot determine source type (keep backward compatibility)
RAW_FIELDNAMES = [
    "id",
    "card_type",
    "front_template",
    "back_template",
    "tags_json",
    "created_at",
]


def _safe_json(s: str | None) -> dict[str, Any] | None:
    if not s or not s.strip():
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def _vocab_row_from_note_fields(
    rank: int,
    fields: dict[str, Any],
    *,
    back_fallback: dict[str, Any] | None = None,
    notes_for_csv: str | None = None,
) -> dict[str, str]:
    examples = fields.get("examples")
    if not isinstance(examples, list):
        examples = []
    row: dict[str, str] = {
        "rank": str(rank),
        "word": (fields.get("word") or "").strip(),
        "reading_kana": (fields.get("reading_kana") or "").strip(),
        "reading_romaji": (fields.get("reading_romaji") or "").strip(),
        "part_of_speech": (fields.get("part_of_speech") or "").strip(),
        "labels": _labels_cell_from_fields(fields),
        "notes": notes_for_csv if notes_for_csv is not None else _notes_cell_for_export(fields, back_fallback),
        "meaning": (fields.get("meaning") or fields.get("english_word") or "").strip(),
    }
    for i in range(1, 6):
        row[f"example_{i}"] = ""
    for i, ex in enumerate(examples[:5]):
        if ex is None:
            continue
        row[f"example_{i + 1}"] = ex.strip() if isinstance(ex, str) else str(ex).strip()
    return row


def _grammar_row_from_note_fields(
    fields: dict[str, Any],
    *,
    back_fallback: dict[str, Any] | None = None,
    notes_for_csv: str | None = None,
) -> dict[str, str]:
    examples = fields.get("examples")
    if not isinstance(examples, list):
        examples = []
    row: dict[str, str] = {
        "japanese_expression": (fields.get("japanese_expression") or "").strip(),
        "english_meaning": (fields.get("english_meaning") or "").strip(),
        "grammar_structure": (fields.get("grammar_structure") or "").strip(),
        "labels": _labels_cell_from_fields(fields),
        "notes": notes_for_csv if notes_for_csv is not None else _notes_cell_for_export(fields, back_fallback),
    }
    for i in range(1, 6):
        row[f"example_{i}"] = ""
    for i, ex in enumerate(examples[:5]):
        row[f"example_{i + 1}"] = (ex.strip() if isinstance(ex, str) else str(ex).strip()) if ex is not None else ""
    return row


def _kanji_row_from_note_fields(
    rank: int,
    fields: dict[str, Any],
    *,
    back_fallback: dict[str, Any] | None = None,
    notes_for_csv: str | None = None,
) -> dict[str, str]:
    examples = fields.get("examples")
    if not isinstance(examples, list):
        examples = []
    rank_val = fields.get("rank")
    if rank_val is not None and str(rank_val).strip():
        rank_str = str(rank_val).strip()
    else:
        rank_str = str(rank)
    row: dict[str, str] = {
        "rank": rank_str,
        "kanji": (fields.get("kanji") or "").strip(),
        "onyomi": (fields.get("onyomi") or "").strip(),
        "kunyomi": (fields.get("kunyomi") or "").strip(),
        "meaning": (fields.get("meaning") or "").strip(),
        "labels": _labels_cell_from_fields(fields),
        "notes": notes_for_csv if notes_for_csv is not None else _notes_cell_for_export(fields, back_fallback),
    }
    for i in range(1, 6):
        row[f"example_{i}"] = ""
    for i, ex in enumerate(examples[:5]):
        if ex is not None:
            row[f"example_{i + 1}"] = ex.strip() if isinstance(ex, str) else str(ex).strip()
    return row


def _vocab_row_from_card_back(rank: int, back: dict[str, Any], *, notes_for_csv: str | None = None) -> dict[str, str]:
    """Build vocab export row from card back_template JSON (fallback when note missing)."""
    examples = back.get("examples")
    if not isinstance(examples, list):
        examples = []
    row: dict[str, str] = {
        "rank": str(rank),
        "word": (back.get("word") or "").strip(),
        "reading_kana": (back.get("reading_kana") or "").strip(),
        "reading_romaji": "",
        "part_of_speech": "",
        "labels": "",
        "notes": notes_for_csv if notes_for_csv is not None else _notes_cell_for_export(back, None),
        "meaning": (back.get("meaning") or "").strip(),
    }
    for i in range(1, 6):
        row[f"example_{i}"] = ""
    for i, ex in enumerate(examples[:5]):
        row[f"example_{i + 1}"] = (ex.strip() if isinstance(ex, str) else str(ex).strip()) if ex is not None else ""
    return row


def _infer_source_type_from_card_type(card_type: str) -> str | None:
    if not card_type:
        return None
    if card_type.startswith("vocab_"):
        return "vocabulary"
    if card_type.startswith("grammar_"):
        return "grammar"
    if card_type.startswith("kanji_"):
        return "kanji"
    return None


def export_deck_csv(conn: Any, deck_id: str, *, export_user_id: str | None = None) -> tuple[str, list[str]]:
    """
    Export deck cards in the same format as import (one row per note).
    Returns (csv_text, fieldnames_used).
    Uses note.source_type and note.fields_json when available; otherwise infers from card_type
    and parses back_template (fallback).
    If export_user_id is set, that user's card_study_notes for cards in this deck are merged into
    the CSV `notes` column (after the deck note from fields/back).
    """
    # Cards with note_id, ordered by created_at so we have stable note order
    raw_cards = conn.execute(
        """
        SELECT id, note_id, card_type, front_template, back_template, tags_json, created_at
        FROM cards
        WHERE deck_id = ? AND note_id IS NOT NULL
        ORDER BY created_at ASC;
        """,
        (deck_id,),
    ).fetchall()
    card_rows = [dict(r) for r in raw_cards]

    study_by_card: dict[str, str] = {}
    if export_user_id:
        study_by_card = _study_notes_by_card_id(conn, export_user_id, deck_id)

    notes_repo = NoteRepository(conn)
    seen_note_ids: set[str] = set()
    ordered_note_ids: list[str] = []
    for r in card_rows:
        nid = (r.get("note_id") or "").strip() if r.get("note_id") else ""
        if nid and nid not in seen_note_ids:
            seen_note_ids.add(nid)
            ordered_note_ids.append(nid)

    if not ordered_note_ids:
        # No notes: fall back to raw format (one row per card) for backward compatibility
        all_cards = conn.execute(
            """
            SELECT id, card_type, front_template, back_template, tags_json, created_at
            FROM cards
            WHERE deck_id = ?
            ORDER BY created_at ASC;
            """,
            (deck_id,),
        ).fetchall()
        rows = []
        for r in all_cards:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])[:10]
            rows.append(d)
        return (
            write_csv(rows, RAW_FIELDNAMES),
            RAW_FIELDNAMES,
        )

    rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    source_type_used: str | None = None

    for rank, note_id in enumerate(ordered_note_ids, start=1):
        note = notes_repo.get_note(note_id)
        if not note:
            continue
        st = (note.get("source_type") or "").strip()
        fields_json = note.get("fields_json")
        fields = _safe_json(fields_json) if fields_json else None
        first_card = next((c for c in card_rows if (c.get("note_id") or "") == note_id), None)
        back_fb = _safe_json(first_card.get("back_template") or "") if first_card else None
        study_bodies = _study_bodies_for_note(study_by_card, card_rows, note_id)
        deck_notes_part = _notes_cell_for_export(fields, back_fb) if fields else ""
        if not fields and first_card:
            back_only = _safe_json(first_card.get("back_template") or "")
            deck_notes_part = _notes_cell_for_export(back_only or {}, None) if back_only else ""
        notes_for_csv = _compose_csv_notes_cell(deck_notes_part, study_bodies)

        if fields and st == "vocabulary":
            if fieldnames and source_type_used != "vocabulary":
                continue
            source_type_used = "vocabulary"
            row = _vocab_row_from_note_fields(rank, fields, back_fallback=back_fb, notes_for_csv=notes_for_csv)
            if not fieldnames:
                fieldnames = list(VOCAB_FIELDNAMES)
            rows.append(row)
        elif fields and st == "grammar":
            if fieldnames and source_type_used != "grammar":
                continue
            source_type_used = "grammar"
            row = _grammar_row_from_note_fields(fields, back_fallback=back_fb, notes_for_csv=notes_for_csv)
            if not fieldnames:
                fieldnames = list(GRAMMAR_FIELDNAMES)
            rows.append(row)
        elif fields and st == "kanji":
            if fieldnames and source_type_used != "kanji":
                continue
            source_type_used = "kanji"
            row = _kanji_row_from_note_fields(rank, fields, back_fallback=back_fb, notes_for_csv=notes_for_csv)
            if not fieldnames:
                fieldnames = list(KANJI_FIELDNAMES)
            rows.append(row)
        else:
            # Note without usable source_type/fields: try first card for this note as fallback
            if fieldnames and source_type_used != "vocabulary":
                continue
            if first_card:
                back = _safe_json(first_card.get("back_template") or "")
                inferred = _infer_source_type_from_card_type(first_card.get("card_type") or "")
                if back and inferred == "vocabulary" and back.get("word") and back.get("meaning") is not None:
                    source_type_used = "vocabulary"
                    row = _vocab_row_from_card_back(rank, back, notes_for_csv=notes_for_csv)
                    if not fieldnames:
                        fieldnames = list(VOCAB_FIELDNAMES)
                    rows.append(row)

    if not rows:
        return write_csv([], RAW_FIELDNAMES), RAW_FIELDNAMES

    # Re-rank so exported rank is 1, 2, 3, ... when we skipped notes of other types
    if "rank" in fieldnames:
        for i, r in enumerate(rows, start=1):
            r["rank"] = str(i)

    # Sanitize all cell values (formula injection prevention)
    safe_rows = []
    for r in rows:
        safe_rows.append({k: sanitize_csv_cell(r.get(k, "")) for k in fieldnames})
    return write_csv(safe_rows, fieldnames), fieldnames
