import os
import tempfile

from app.db import ensure_db, run_migrations, connection
from app.repositories.card_study_notes import CardStudyNoteRepository
from app.repositories.cards import CardRepository
from app.repositories.decks import DeckRepository
from app.repositories.events import EventRepository
from app.repositories.notes import NoteRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository


def _new_db_path() -> str:
    fd, path = tempfile.mkstemp(prefix="furikaeri_test_", suffix=".sqlite")
    os.close(fd)
    return path


def test_migrations_idempotent():
    path = _new_db_path()
    ensure_db(path)
    info1 = run_migrations(path)
    info2 = run_migrations(path)
    assert info1["current_version"] >= 1
    assert info2["current_version"] == info1["current_version"]
    assert info2["applied"] == []


def test_repositories_basic_flow():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)

    with connection(path) as conn:
        conn.execute("BEGIN;")
        try:
            users = UserRepository(conn)
            decks = DeckRepository(conn)
            notes = NoteRepository(conn)
            cards = CardRepository(conn)
            reviews = ReviewRepository(conn)
            events = EventRepository(conn)

            user_id = users.ensure_single_user()
            assert users.get_user(user_id)["id"] == user_id

            deck_id = decks.create_deck(name="N5 Grammar", description="Test deck")
            assert decks.get_deck(deck_id)["name"] == "N5 Grammar"

            note_id = notes.upsert_note(
                source_type="grammar",
                level="N5",
                key="だ / です",
                fields_json='{"japanese_expression":"だ / です"}',
                source_url="https://example.com",
            )
            assert notes.get_note(note_id)["source_type"] == "grammar"

            card_id = cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="meaning_recognition")
            deck_cards = cards.list_cards_for_deck(deck_id, limit=10)
            assert any(c["id"] == card_id for c in deck_cards)

            reviews.upsert_review_state(card_id=card_id, user_id=user_id, due_at="2026-01-01T00:00:00Z", stability=1.2)
            rs = reviews.get_review_state(card_id, user_id)
            assert rs is not None
            assert float(rs["stability"]) == 1.2

            ev_id = events.append_event(user_id=user_id, event_type="card_shown", payload_json="{}")
            row = conn.execute("SELECT event_id FROM events WHERE event_id = ?;", (ev_id,)).fetchone()
            assert row is not None
        finally:
            conn.execute("ROLLBACK;")


def test_card_study_notes_upsert_get_delete():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        users = UserRepository(conn)
        decks = DeckRepository(conn)
        notes = NoteRepository(conn)
        cards = CardRepository(conn)
        study_notes = CardStudyNoteRepository(conn)
        user_id = users.ensure_single_user()
        deck_id = decks.create_deck(name="D", description="")
        note_id = notes.upsert_note(source_type="grammar", level="N5", key="x", fields_json="{}")
        card_id = cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="grammar_meaning_recognition")
        assert study_notes.get_for_user(user_id=user_id, card_id=card_id) is None
        row = study_notes.upsert(user_id=user_id, card_id=card_id, body="first")
        assert row["body"] == "first"
        row2 = study_notes.upsert(user_id=user_id, card_id=card_id, body="second")
        assert row2["body"] == "second"
        assert study_notes.get_for_user(user_id=user_id, card_id=card_id)["body"] == "second"
        assert study_notes.delete_for_user(user_id=user_id, card_id=card_id) is True
        assert study_notes.get_for_user(user_id=user_id, card_id=card_id) is None
        assert study_notes.delete_for_user(user_id=user_id, card_id=card_id) is False
    os.remove(path)


def test_notes_list_notes_and_get_note_by_key():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        notes = NoteRepository(conn)
        notes.upsert_note(source_type="grammar", level="N5", key="k1", fields_json="{}")
        notes.upsert_note(source_type="grammar", level="N4", key="k2", fields_json="{}")
        all_notes = notes.list_notes(limit=10)
        assert len(all_notes) >= 2
        by_level = notes.list_notes(source_type="grammar", level="N5", limit=10)
        assert len(by_level) >= 1
        assert all(n["level"] == "N5" for n in by_level)
        row = notes.get_note_by_key(source_type="grammar", level="N5", key="k1")
        assert row is not None
        assert row["key"] == "k1"
    os.remove(path)


def test_sessions_create_mark_seen_end():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        users = UserRepository(conn)
        decks = DeckRepository(conn)
        cards = CardRepository(conn)
        reviews = ReviewRepository(conn)
        sessions = SessionRepository(conn)
        user_id = users.ensure_single_user()
        deck_id = decks.create_deck(name="D", description="")
        note_id = NoteRepository(conn).upsert_note(source_type="grammar", level="N5", key="x", fields_json="{}")
        card_id = cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="meaning")
        reviews.upsert_review_state(card_id=card_id, user_id=user_id, due_at="2026-01-01T00:00:00Z")
        sid = sessions.create_session(user_id=user_id, deck_id=deck_id, mode="mixed", new_limit=5)
        assert sid
        sess = sessions.get_session(sid)
        assert sess["deck_id"] == deck_id
        assert sess["include_listening"] == 1
        sid2 = sessions.create_session(user_id=user_id, deck_id=deck_id, mode="mixed", new_limit=3, include_listening=False)
        sess2 = sessions.get_session(sid2)
        assert sess2["include_listening"] == 0
        assert sessions.is_seen(session_id=sid, card_id=card_id) is False
        sessions.mark_seen(session_id=sid, card_id=card_id)
        assert sessions.is_seen(session_id=sid, card_id=card_id) is True
        sessions.increment_new_shown(session_id=sid)
        sessions.end_session(session_id=sid)
        sess2 = sessions.get_session(sid)
        assert sess2["ended_at"] is not None
    os.remove(path)


def test_cards_delete_placeholders_and_except_types():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        decks = DeckRepository(conn)
        notes = NoteRepository(conn)
        cards = CardRepository(conn)
        deck_id = decks.create_deck(name="D", description="")
        note_id = notes.upsert_note(source_type="grammar", level="N5", key="x", fields_json="{}")
        c1 = cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="meaning_recognition")
        cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="old_placeholder")
        n = cards.delete_placeholders_for_note(note_id=note_id, deck_id=deck_id)
        assert n >= 1
        n2 = cards.delete_cards_for_note_except_types(note_id=note_id, deck_id=deck_id, keep_card_types={"meaning_recognition"})
        assert n2 >= 0
        list_cards = cards.list_cards_for_deck(deck_id, limit=10)
        assert any(c["id"] == c1 for c in list_cards)
    os.remove(path)


def test_cards_search_by_text_and_like_escape():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        decks = DeckRepository(conn)
        notes = NoteRepository(conn)
        cards = CardRepository(conn)
        deck_id = decks.create_deck(name="D", description="")
        note_id = notes.upsert_note(source_type="grammar", level="N5", key="x", fields_json="{}")
        cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="m", front_template='{"word":"hello"}', back_template="{}")
        results = cards.search_cards_by_text("hello", limit=10)
        assert len(results) >= 1
        assert results[0].get("deck_name") == "D"
        empty = cards.search_cards_by_text("", limit=10)
        assert empty == []
        long_q = cards.search_cards_by_text("x" * 201, limit=10)
        assert long_q == []
    os.remove(path)


def test_cards_delete_except_types_empty_keep_returns_zero():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        decks = DeckRepository(conn)
        notes = NoteRepository(conn)
        cards = CardRepository(conn)
        deck_id = decks.create_deck(name="D", description="")
        note_id = notes.upsert_note(source_type="grammar", level="N5", key="x", fields_json="{}")
        cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="m")
        n = cards.delete_cards_for_note_except_types(note_id=note_id, deck_id=deck_id, keep_card_types=set())
        assert n == 0
    os.remove(path)


def test_cards_count_due_and_new():
    path = _new_db_path()
    ensure_db(path)
    run_migrations(path)
    with connection(path) as conn:
        users = UserRepository(conn)
        decks = DeckRepository(conn)
        notes = NoteRepository(conn)
        cards = CardRepository(conn)
        reviews = ReviewRepository(conn)
        user_id = users.ensure_single_user()
        deck_id = decks.create_deck(name="D", description="")
        note_id = notes.upsert_note(source_type="grammar", level="N5", key="x", fields_json="{}")
        card_id = cards.upsert_card(note_id=note_id, deck_id=deck_id, card_type="grammar_meaning_recognition")
        reviews.upsert_review_state(card_id=card_id, user_id=user_id, due_at="2025-01-01T00:00:00Z")
        n_due = cards.count_due_now(deck_id=deck_id, user_id=user_id, now_iso="2026-01-01T00:00:00Z")
        assert n_due >= 1
        n_today = cards.count_due_today(deck_id=deck_id, user_id=user_id, start_iso="2025-01-01T00:00:00Z", end_iso="2026-01-02T00:00:00Z")
        assert n_today >= 1
        cards.count_new_available(deck_id=deck_id, user_id=user_id)
    os.remove(path)
