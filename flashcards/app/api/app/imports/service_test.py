"""Tests for app.imports.service."""

import os
import tempfile

import pytest

from app.db import ensure_db, run_migrations, connection
from app.imports.adapters import ImportItem
from app.imports.service import import_items_into_deck, sync_items_into_deck


def _temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    return path


def test_import_items_deck_name_empty_raises() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            with pytest.raises(ValueError, match="deck_name"):
                import_items_into_deck(
                    conn=conn,
                    level="N5",
                    deck_name="",
                    source_type="grammar",
                    items=[],
                    merge_policy="overwrite",
                )
    finally:
        os.remove(path)


def test_import_items_level_invalid_raises() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            with pytest.raises(ValueError, match="level"):
                import_items_into_deck(
                    conn=conn,
                    level="",
                    deck_name="Test",
                    source_type="grammar",
                    items=[],
                    merge_policy="overwrite",
                )
    finally:
        os.remove(path)


def test_import_items_merge_policy_invalid_raises() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            with pytest.raises(ValueError, match="merge_policy"):
                import_items_into_deck(
                    conn=conn,
                    level="N5",
                    deck_name="Test",
                    source_type="grammar",
                    items=[],
                    merge_policy="invalid",
                )
    finally:
        os.remove(path)


def test_import_items_empty_items_creates_deck_only() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            result = import_items_into_deck(
                conn=conn,
                level="N5",
                deck_name="Empty Deck",
                source_type="grammar",
                items=[],
                merge_policy="overwrite",
            )
            assert result["deck_name"] == "Empty Deck"
            assert result["level"] == "N5"
            assert result["created_notes"] == 0
            assert result["created_cards"] == 0
            assert result["deck_id"] is not None
    finally:
        os.remove(path)


def test_import_items_one_grammar_item() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            items = [
                ImportItem(
                    source_type="grammar",
                    level="N5",
                    key="だ",
                    fields={
                        "japanese_expression": "だ",
                        "english_meaning": "to be",
                        "grammar_structure": "Noun + だ",
                        "examples": [],
                    },
                ),
            ]
            result = import_items_into_deck(
                conn=conn,
                level="N5",
                deck_name="Grammar Deck",
                source_type="grammar",
                items=items,
                merge_policy="overwrite",
            )
            assert result["created_notes"] == 1
            assert result["created_cards"] >= 1
            assert result["deck_name"] == "Grammar Deck"
    finally:
        os.remove(path)


def test_import_items_deck_name_too_long_raises() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            with pytest.raises(ValueError, match="deck_name"):
                import_items_into_deck(
                    conn=conn,
                    level="N5",
                    deck_name="x" * 121,
                    source_type="grammar",
                    items=[],
                    merge_policy="overwrite",
                )
    finally:
        os.remove(path)


def test_import_items_level_too_long_raises() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            with pytest.raises(ValueError, match="level"):
                import_items_into_deck(
                    conn=conn,
                    level="x" * 17,
                    deck_name="Test",
                    source_type="grammar",
                    items=[],
                    merge_policy="overwrite",
                )
    finally:
        os.remove(path)


def test_import_items_keep_both_unique_keys() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            # Two items with same key so second gets "だ (2)"; use different expressions so card_ids differ.
            items = [
                ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": []}),
                ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "です", "english_meaning": "to be (polite)", "grammar_structure": "", "examples": []}),
            ]
            result = import_items_into_deck(
                conn=conn, level="N5", deck_name="Deck", source_type="grammar", items=items, merge_policy="keep_both",
            )
            assert result["created_notes"] == 2
            assert result["created_cards"] >= 2
    finally:
        os.remove(path)


def test_import_items_merge_examples() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            from app.repositories.notes import NoteRepository

            notes = NoteRepository(conn)
            items1 = [
                ImportItem(
                    source_type="grammar",
                    level="N5",
                    key="だ",
                    fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": ["ex1"]},
                ),
            ]
            import_items_into_deck(conn=conn, level="N5", deck_name="D", source_type="grammar", items=items1, merge_policy="overwrite")
            items2 = [
                ImportItem(
                    source_type="grammar",
                    level="N5",
                    key="だ",
                    fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": ["ex2", "ex1"]},
                ),
            ]
            result = import_items_into_deck(conn=conn, level="N5", deck_name="D", source_type="grammar", items=items2, merge_policy="merge_examples")
            assert result["updated_notes"] == 1
            row = notes.get_note_by_key(source_type="grammar", level="N5", key="だ")
            import json
            merged = json.loads(row["fields_json"])
            assert "ex1" in merged.get("examples", []) and "ex2" in merged.get("examples", [])
    finally:
        os.remove(path)


def test_import_items_merge_examples_malformed_json_overwrites() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            conn.execute(
                "INSERT INTO notes(id, source_type, level, key, fields_json, source_url, created_at) VALUES(?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));",
                ("n1", "grammar", "N5", "だ", "not valid json", None),
            )
            conn.commit()
            items = [
                ImportItem(
                    source_type="grammar",
                    level="N5",
                    key="だ",
                    fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": ["new"]},
                ),
            ]
            result = import_items_into_deck(conn=conn, level="N5", deck_name="D", source_type="grammar", items=items, merge_policy="merge_examples")
            assert result["updated_notes"] == 1
    finally:
        os.remove(path)


# --- sync_items_into_deck ---


def test_sync_items_deck_not_found_raises() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            with pytest.raises(ValueError, match="deck not found"):
                sync_items_into_deck(
                    conn=conn,
                    deck_id="nonexistent-deck-id",
                    level="N5",
                    source_type="grammar",
                    items=[],
                )
    finally:
        os.remove(path)


def test_sync_items_new_only() -> None:
    """Sync into existing deck with only new items; all created."""
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            from app.repositories.decks import DeckRepository

            decks = DeckRepository(conn)
            deck_id = decks.create_deck(name="Sync Deck", description="Imported grammar (N5)")
            conn.commit()
            items = [
                ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": []}),
                ImportItem(source_type="grammar", level="N5", key="です", fields={"japanese_expression": "です", "english_meaning": "is", "grammar_structure": "", "examples": []}),
            ]
            result = sync_items_into_deck(conn=conn, deck_id=deck_id, level="N5", source_type="grammar", items=items, merge_existing="skip")
            assert result["deck_id"] == deck_id
            assert result["deck_name"] == "Sync Deck"
            assert result["created_notes"] == 2
            assert result["updated_notes"] == 0
            assert result["skipped"] == 0
            assert result["created_cards"] >= 2
    finally:
        os.remove(path)


def test_sync_items_skip_existing() -> None:
    """Sync with skip: existing key is skipped, new key is added."""
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            result = import_items_into_deck(
                conn=conn,
                level="N5",
                deck_name="D",
                source_type="grammar",
                items=[ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": []})],
                merge_policy="overwrite",
            )
            deck_id = result["deck_id"]
            conn.commit()
            items = [
                ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": []}),
                ImportItem(source_type="grammar", level="N5", key="です", fields={"japanese_expression": "です", "english_meaning": "is", "grammar_structure": "", "examples": []}),
            ]
            result2 = sync_items_into_deck(conn=conn, deck_id=deck_id, level="N5", source_type="grammar", items=items, merge_existing="skip")
            assert result2["created_notes"] == 1
            assert result2["skipped"] == 1
            assert result2["created_cards"] >= 1
    finally:
        os.remove(path)


def test_sync_items_merge_examples() -> None:
    """Sync with merge_examples: existing note gets examples merged."""
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            from app.repositories.notes import NoteRepository

            notes = NoteRepository(conn)
            result = import_items_into_deck(
                conn=conn,
                level="N5",
                deck_name="D",
                source_type="grammar",
                items=[ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": ["ex1"]})],
                merge_policy="overwrite",
            )
            deck_id = result["deck_id"]
            conn.commit()
            items = [
                ImportItem(source_type="grammar", level="N5", key="だ", fields={"japanese_expression": "だ", "english_meaning": "to be", "grammar_structure": "", "examples": ["ex2", "ex1"]}),
            ]
            result2 = sync_items_into_deck(conn=conn, deck_id=deck_id, level="N5", source_type="grammar", items=items, merge_existing="merge_examples")
            assert result2["updated_notes"] == 1
            assert result2["skipped"] == 0
            row = notes.get_note_by_key(source_type="grammar", level="N5", key="だ")
            import json as _json
            merged = _json.loads(row["fields_json"])
            assert "ex1" in merged.get("examples", []) and "ex2" in merged.get("examples", [])
    finally:
        os.remove(path)
