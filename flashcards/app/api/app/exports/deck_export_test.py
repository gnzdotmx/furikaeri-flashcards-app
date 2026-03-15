"""Tests for app.exports.deck_export."""

import json
import os
import tempfile
from pathlib import Path

from app.db import connection, ensure_db, run_migrations
from app.exports.deck_export import (
    export_deck_csv,
    GRAMMAR_FIELDNAMES,
    KANJI_FIELDNAMES,
    RAW_FIELDNAMES,
    VOCAB_FIELDNAMES,
)
from app.imports.adapters import encode_fields_json
from app.repositories.cards import CardRepository
from app.repositories.decks import DeckRepository
from app.repositories.notes import NoteRepository


def _temp_db() -> str:
    return str(Path(tempfile.mkdtemp(prefix="deck_export_test_")) / "test.sqlite")


def test_export_empty_deck_returns_raw_header() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            deck_id = DeckRepository(conn).create_deck(name="Empty", description="")
            conn.commit()
            csv_text, fieldnames = export_deck_csv(conn, deck_id)
        assert fieldnames == RAW_FIELDNAMES
        lines = csv_text.strip().splitlines()
        assert len(lines) == 1
        assert lines[0] == "id,card_type,front_template,back_template,tags_json,created_at"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_export_vocabulary_deck_returns_import_format() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            decks = DeckRepository(conn)
            notes_repo = NoteRepository(conn)
            cards_repo = CardRepository(conn)
            deck_id = decks.create_deck(name="Vocab", description="")
            conn.commit()

            fields = {
                "word": "大切",
                "reading_kana": "たいせつ",
                "reading_romaji": "taisetsu",
                "part_of_speech": "Adjective",
                "meaning": "important",
                "examples": ["ex1 sentence", "ex2"],
            }
            note_id = notes_repo.upsert_note(
                source_type="vocabulary",
                level="N5",
                key="大切|たいせつ|important",
                fields_json=encode_fields_json(fields),
            )
            conn.commit()

            cards_repo.upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type="vocab_meaning_recall",
                front_template='{"word":"大切"}',
                back_template=json.dumps({"word": "大切", "reading_kana": "たいせつ", "meaning": "important", "examples": ["ex1", "ex2"]}),
            )
            cards_repo.upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type="vocab_reading_recall",
                front_template='{"word":"大切"}',
                back_template=json.dumps({"word": "大切", "reading_kana": "たいせつ", "meaning": "important", "examples": ["ex1", "ex2"]}),
            )
            conn.commit()

            csv_text, fieldnames = export_deck_csv(conn, deck_id)

        assert fieldnames == VOCAB_FIELDNAMES
        lines = csv_text.strip().splitlines()
        assert len(lines) >= 2
        header = lines[0]
        assert "rank" in header and "word" in header and "reading_kana" in header
        assert "reading_romaji" in header and "meaning" in header and "example_1" in header
        data_row = lines[1]
        assert "大切" in data_row
        assert "たいせつ" in data_row
        assert "taisetsu" in data_row
        assert "important" in data_row
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_export_grammar_deck_returns_import_format() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            decks = DeckRepository(conn)
            notes_repo = NoteRepository(conn)
            cards_repo = CardRepository(conn)
            deck_id = decks.create_deck(name="Grammar", description="")
            conn.commit()

            fields = {
                "japanese_expression": "だ",
                "english_meaning": "to be",
                "grammar_structure": "Noun + だ",
                "examples": ["これは本だ。", "That is a book."],
            }
            note_id = notes_repo.upsert_note(
                source_type="grammar",
                level="N5",
                key="だ",
                fields_json=encode_fields_json(fields),
            )
            conn.commit()

            cards_repo.upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type="grammar_meaning_recognition",
                front_template="{}",
                back_template="{}",
            )
            conn.commit()

            csv_text, fieldnames = export_deck_csv(conn, deck_id)

        assert fieldnames == GRAMMAR_FIELDNAMES
        lines = csv_text.strip().splitlines()
        assert len(lines) >= 2
        assert "japanese_expression" in lines[0]
        assert "だ" in lines[1]
        assert "to be" in lines[1]
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_export_kanji_deck_returns_import_format() -> None:
    path = _temp_db()
    try:
        ensure_db(path)
        run_migrations(path)
        with connection(path) as conn:
            decks = DeckRepository(conn)
            notes_repo = NoteRepository(conn)
            cards_repo = CardRepository(conn)
            deck_id = decks.create_deck(name="Kanji", description="")
            conn.commit()

            fields = {
                "rank": "1",
                "kanji": "日",
                "onyomi": "ニチ",
                "kunyomi": "ひ",
                "meaning": "day sun",
                "examples": ["日本"],
            }
            note_id = notes_repo.upsert_note(
                source_type="kanji",
                level="N5",
                key="日",
                fields_json=encode_fields_json(fields),
            )
            conn.commit()

            cards_repo.upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type="kanji_reading_recall",
                front_template="{}",
                back_template="{}",
            )
            conn.commit()

            csv_text, fieldnames = export_deck_csv(conn, deck_id)

        assert fieldnames == KANJI_FIELDNAMES
        lines = csv_text.strip().splitlines()
        assert len(lines) >= 2
        assert "kanji" in lines[0] and "onyomi" in lines[0]
        assert "日" in lines[1]
    finally:
        if os.path.exists(path):
            os.remove(path)
