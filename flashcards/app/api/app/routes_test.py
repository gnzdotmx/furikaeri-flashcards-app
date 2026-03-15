"""Tests for app.routes (API endpoints)."""

import io
import os
import tempfile
from pathlib import Path
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import create_app
from app.routes import router as api_router


@pytest.fixture(autouse=True)
def _bypass_rate_limit_in_tests():
    """Set TESTING=1 so rate_limit_middleware skips limits (avoids 429 in import/sync tests)."""
    old = os.environ.get("TESTING")
    os.environ["TESTING"] = "1"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("TESTING", None)
        else:
            os.environ["TESTING"] = old


# JWT secret for tests (required by settings; at least 32 chars for HS256).
_TEST_JWT_SECRET = "test-jwt-secret-at-least-32-bytes-for-hs256"


class _AuthClient:
    """Wraps TestClient and injects Authorization header for protected API routes."""

    def __init__(self, client: TestClient, token: str):
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    def _merge_headers(self, kwargs):
        h = kwargs.get("headers") or {}
        return {**self._headers, **h}

    def get(self, url, **kwargs):
        kwargs["headers"] = self._merge_headers(kwargs)
        return self._client.get(url, **kwargs)

    def post(self, url, **kwargs):
        kwargs["headers"] = self._merge_headers(kwargs)
        return self._client.post(url, **kwargs)

    def put(self, url, **kwargs):
        kwargs["headers"] = self._merge_headers(kwargs)
        return self._client.put(url, **kwargs)

    def patch(self, url, **kwargs):
        kwargs["headers"] = self._merge_headers(kwargs)
        return self._client.patch(url, **kwargs)

    def delete(self, url, **kwargs):
        kwargs["headers"] = self._merge_headers(kwargs)
        return self._client.delete(url, **kwargs)

    @property
    def app(self):
        return self._client.app

    @property
    def cookies(self):
        return self._client.cookies


def _test_client():
    """Create a test client with a unique DB so the app and test use the same DB."""
    tmp = Path(tempfile.mkdtemp(prefix="furikaeri_routes_"))
    db_path = str(tmp / "test.sqlite")
    os.environ["SQLITE_PATH"] = db_path
    os.environ["DATA_DIR"] = str(tmp)
    os.environ["AUDIO_CACHE_DIR"] = str(tmp / "audio_cache")
    os.environ["JWT_SECRET"] = _TEST_JWT_SECRET
    app = create_app()
    return TestClient(app)


def _test_client_with_auth():
    """Client that has registered a user and sends Bearer token on every request."""
    client = _test_client()
    r = client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "pass123456"},
    )
    assert r.status_code == 200, (r.status_code, r.text)
    token = r.json()["access_token"]
    return _AuthClient(client, token)


def _test_client_same_db():
    """
    Client and DB path guaranteed to be the same; client is authenticated.
    Yields (client, sqlite_path).
    """
    client = _test_client()
    r = client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "pass123456"},
    )
    assert r.status_code == 200, (r.status_code, r.text)
    token = r.json()["access_token"]
    auth_client = _AuthClient(client, token)
    app = getattr(client, "app", None)
    db_path = getattr(app.state, "sqlite_path", None) if app else None
    if not db_path:
        db_path = str(Path(os.environ["SQLITE_PATH"]).resolve())
    yield auth_client, db_path


def _sqlite_path():
    return os.environ["SQLITE_PATH"]


# --- Routes package structure ---


def test_routes_package_exposes_expected_paths():
    """Ensure the modular routes package registers all expected API path prefixes."""
    # Paths that must exist when app is mounted with prefix /api
    expected_prefixes = (
        "/auth/register",
        "/auth/login",
        "/auth/logout",
        "/auth/me",
        "/sessions/start",
        "/sessions/{session_id}/next",
        "/sessions/{session_id}/answer",
        "/decks",
        "/decks/{deck_id}/cards",
        "/decks/{deck_id}/leeches",
        "/decks/{deck_id}/labels",
        "/cards/{card_id}/suspend",
        "/search/examples",
        "/notes",
        "/exports/decks/{deck_id}/cards.csv",
        "/events",
        "/users/settings",
        "/metrics/summary",
        "/tts/to-kana",
        "/tts",
        "/imports/sync",
        "/imports/grammar",
        "/imports/kanji",
        "/imports/vocabulary",
    )
    routes = [r.path for r in api_router.routes if hasattr(r, "path")]
    for prefix in expected_prefixes:
        assert any(prefix in p or p == prefix for p in routes), f"Expected path like {prefix!r} in registered routes: {routes[:5]}..."


# --- Decks & cards ---


def test_api_decks_require_auth() -> None:
    """Protected routes return 401 without Bearer token."""
    client = _test_client()
    res = client.get("/api/decks")
    assert res.status_code == 401


def test_api_decks_list() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/decks")
    assert res.status_code == 200
    data = res.json()
    assert "decks" in data


def test_api_deck_cards_empty() -> None:
    from app.db import connection
    from app.repositories.decks import DeckRepository

    client = _test_client_with_auth()
    with connection(_sqlite_path()) as conn:
        deck_id = DeckRepository(conn).create_deck(name="RTest", description="")
        conn.commit()
    res = client.get(f"/api/decks/{deck_id}/cards")
    assert res.status_code == 200
    data = res.json()
    assert "cards" in data
    assert "counts_by_type" in data


def test_api_deck_labels_empty() -> None:
  from app.db import connection
  from app.repositories.decks import DeckRepository
  for client, db_path in _test_client_same_db():
      with connection(db_path) as conn:
          deck_id = DeckRepository(conn).create_deck(name="Labels", description="")
          conn.commit()
      res = client.get(f"/api/decks/{deck_id}/labels")
      break
  assert res.status_code == 200
  data = res.json()
  assert data["deck_id"] == deck_id
  assert data["labels"] == []


def test_api_deck_cards_deck_id_too_long() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/decks/" + "x" * 81 + "/cards")
    assert res.status_code == 400


def test_api_search_examples() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/search/examples?q=test&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "cards" in data
    assert data["query"] == "test"


def test_api_version() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/version")
    assert res.status_code == 200
    data = res.json()
    assert "app_version" in data


# --- Notes ---


def test_api_notes_list() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/notes")
    assert res.status_code == 200
    data = res.json()
    assert "notes" in data
    res2 = client.get("/api/notes?source_type=grammar&level=N5")
    assert res2.status_code == 200


def test_api_notes_invalid_source_type() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/notes?source_type=invalid")
    assert res.status_code == 400


def test_api_notes_level_too_long() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/notes?level=" + "x" * 17)
    assert res.status_code == 400


# --- Sessions ---


def test_api_sessions_start_success() -> None:
    from app.db import connection
    from app.repositories.decks import DeckRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            deck_id = DeckRepository(conn).create_deck(name="Study", description="")
            conn.commit()
        res = client.post("/api/sessions/start", json={"deck_id": deck_id, "mode": "mixed"})
        break
    assert res.status_code == 200
    data = res.json()
    assert "session_id" in data
    assert data["deck"]["id"] == deck_id
    assert "due_now" in data
    assert "new_available" in data


def test_api_sessions_start_deck_not_found() -> None:
    client = _test_client_with_auth()
    res = client.post("/api/sessions/start", json={"deck_id": "nonexistent-deck-id"})
    assert res.status_code == 404


def test_api_sessions_next_not_found() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/sessions/nonexistent-session-id/next")
    assert res.status_code == 404


def test_api_sessions_next_id_too_long() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/sessions/" + "x" * 81 + "/next")
    assert res.status_code == 400


def test_api_sessions_next_returns_done_when_no_cards() -> None:
    from app.db import connection
    from app.repositories.decks import DeckRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            deck_id = DeckRepository(conn).create_deck(name="Empty", description="")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id})
        break
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    res = client.get(f"/api/sessions/{session_id}/next")
    assert res.status_code == 200
    assert res.json()["kind"] == "done"


def test_api_sessions_answer_not_found() -> None:
    client = _test_client_with_auth()
    res = client.post(
        "/api/sessions/fake-session/answer",
        json={"card_id": "fake-card", "rating": "good", "time_ms": 1000},
    )
    assert res.status_code == 404


def test_api_sessions_answer_session_id_too_long() -> None:
    client = _test_client_with_auth()
    res = client.post(
        "/api/sessions/" + "x" * 81 + "/answer",
        json={"card_id": "some-card", "rating": "good", "time_ms": 1000},
    )
    assert res.status_code == 400
    assert "session_id" in (res.json().get("detail") or "").lower()


def test_api_sessions_answer_logs_warning_when_bandit_fails_but_returns_200() -> None:
    """When Bandit/FSRS update raises, answer is still saved and we log a warning."""
    from unittest.mock import patch

    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="LogTest", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="grammar", level="N5", key="k", fields_json="{}")
            card_id = CardRepository(conn).upsert_card(note_id=note_id, deck_id=deck_id, card_type="grammar_meaning_recognition")
            ReviewRepository(conn).upsert_review_state(card_id=card_id, user_id=user_id, due_at="2020-01-01T00:00:00Z")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id})
        assert start.status_code == 200
        session_id = start.json()["session_id"]
        next_res = client.get(f"/api/sessions/{session_id}/next")
        assert next_res.status_code == 200
        if next_res.json().get("kind") == "done":
            pytest.skip("no card in session")
        card_id = next_res.json()["card"]["id"]
        with patch("app.services.session_service.logger") as mock_log:
            with patch("app.services.session_service.BanditRepository") as mock_bandit_cls:
                mock_repo = mock_bandit_cls.return_value
                mock_repo.update_arm.side_effect = RuntimeError("Bandit update failed")
                res = client.post(
                    f"/api/sessions/{session_id}/answer",
                    json={"card_id": card_id, "rating": "good", "time_ms": 1000},
                )
        assert res.status_code == 200
        assert res.json().get("ok") is True
        mock_log.warning.assert_called_once()
        call_msg = mock_log.warning.call_args[0][0]
        assert "Bandit" in call_msg or "answer still saved" in call_msg
        break


def test_api_sessions_full_flow_one_card() -> None:
    """Start session, get next (one card), submit answer."""
    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="Flow", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="grammar", level="N5", key="k", fields_json="{}")
            card_id = CardRepository(conn).upsert_card(note_id=note_id, deck_id=deck_id, card_type="grammar_meaning_recognition")
            ReviewRepository(conn).upsert_review_state(card_id=card_id, user_id=user_id, due_at="2020-01-01T00:00:00Z")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id})
        break
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    next_res = client.get(f"/api/sessions/{session_id}/next")
    assert next_res.status_code == 200
    data = next_res.json()
    if data["kind"] == "done":
        return
    assert data["kind"] in ("due", "new", "learning")
    card_id = data["card"]["id"]
    answer = client.post(
        f"/api/sessions/{session_id}/answer",
        json={"card_id": card_id, "rating": "good", "time_ms": 1500},
    )
    assert answer.status_code == 200
    assert answer.json()["ok"] is True
    assert "next_due_at" in answer.json()


def test_api_sessions_integration_start_next_answer_next_or_done() -> None:
    """Integration: start session → get next card → submit answer → get next (card or done)."""
    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="Integration", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="grammar", level="N5", key="int1", fields_json="{}")
            card_id = CardRepository(conn).upsert_card(note_id=note_id, deck_id=deck_id, card_type="grammar_meaning_recognition")
            ReviewRepository(conn).upsert_review_state(card_id=card_id, user_id=user_id, due_at="2020-01-01T00:00:00Z")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id})
        assert start.status_code == 200, start.text
        session_id = start.json()["session_id"]

        next1 = client.get(f"/api/sessions/{session_id}/next")
        assert next1.status_code == 200
        data1 = next1.json()
        assert data1["kind"] in ("done", "due", "new", "learning")

        if data1["kind"] == "done":
            return

        card_id = data1["card"]["id"]
        answer = client.post(
            f"/api/sessions/{session_id}/answer",
            json={"card_id": card_id, "rating": "good", "time_ms": 1000},
        )
        assert answer.status_code == 200
        assert answer.json().get("ok") is True

        next2 = client.get(f"/api/sessions/{session_id}/next")
        assert next2.status_code == 200
        data2 = next2.json()
        assert data2["kind"] in ("done", "due", "new", "learning")
        break


def test_api_sessions_next_with_label_filter_does_not_error() -> None:
    """Start a session and call /sessions/{id}/next with a label filter; must not raise SQL ESCAPE errors."""
    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="LabelDeck", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="grammar", level="N5", key="k", fields_json="{}")
            # Store a label:* tag in tags_json so label filter has a match target.
            card_id = CardRepository(conn).upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type="grammar_meaning_recognition",
                tags_json='["source:grammar","level:N5","type:grammar_meaning_recognition","label:test_label"]',
            )
            ReviewRepository(conn).upsert_review_state(
                card_id=card_id,
                user_id=user_id,
                due_at="2020-01-01T00:00:00Z",
            )
            conn.commit()
        # Start a session normally
        start = client.post("/api/sessions/start", json={"deck_id": deck_id})
        assert start.status_code == 200
        session_id = start.json()["session_id"]
        # Request next card with label filter; this used to surface a sqlite ESCAPE error if SQL was invalid.
        next_res = client.get(f"/api/sessions/{session_id}/next?label=label:test_label")
        assert next_res.status_code == 200
        data = next_res.json()
        if data["kind"] != "done":
            assert data["card"]["id"] == card_id
        break


def test_api_sessions_start_include_listening_false_excludes_listening_cards() -> None:
    """When include_listening is false, vocab_listening cards are not shown in the session."""
    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="Listen", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="vocab", level="N5", key="k", fields_json="{}")
            card_id = CardRepository(conn).upsert_card(note_id=note_id, deck_id=deck_id, card_type="vocab_listening")
            ReviewRepository(conn).upsert_review_state(card_id=card_id, user_id=user_id, due_at="2020-01-01T00:00:00Z")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id, "include_listening": False})
        break
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    next_res = client.get(f"/api/sessions/{session_id}/next")
    assert next_res.status_code == 200
    # Only card is listening and we excluded it, so session is done
    assert next_res.json()["kind"] == "done"


def test_api_sessions_start_include_listening_true_includes_listening_cards() -> None:
    """When include_listening is true (default), listening cards can be shown."""
    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="Mix", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="vocab", level="N5", key="k", fields_json="{}")
            card_id = CardRepository(conn).upsert_card(note_id=note_id, deck_id=deck_id, card_type="vocab_listening")
            ReviewRepository(conn).upsert_review_state(card_id=card_id, user_id=user_id, due_at="2020-01-01T00:00:00Z")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id, "include_listening": True})
        break
    assert start.status_code == 200
    session_id = start.json()["session_id"]
    next_res = client.get(f"/api/sessions/{session_id}/next")
    assert next_res.status_code == 200
    data = next_res.json()
    assert data["kind"] in ("due", "new", "learning")
    assert data["card"]["card_type"] == "vocab_listening"


# --- Events ---


def test_api_events_success() -> None:
    client = _test_client_with_auth()
    res = client.post(
        "/api/events",
        json={"event_type": "hint_toggled", "payload": {}},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True
    res2 = client.post("/api/events", json={"event_type": "audio_played", "card_id": "c1"})
    assert res2.status_code == 200
    res3 = client.post("/api/events", json={"event_type": "reveal_toggled"})
    assert res3.status_code == 200


def test_api_events_unsupported_type() -> None:
    client = _test_client_with_auth()
    res = client.post("/api/events", json={"event_type": "invalid_type"})
    assert res.status_code == 400


# --- Export CSV ---


def test_api_export_deck_csv_requires_auth() -> None:
    """Export CSV is under /api and must return 401 without Bearer token."""
    client = _test_client()
    res = client.get("/api/exports/decks/some-deck-id/cards.csv")
    assert res.status_code == 401


def test_api_export_deck_csv_success() -> None:
    from app.db import connection
    from app.repositories.decks import DeckRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            deck_id = DeckRepository(conn).create_deck(name="Export", description="")
            conn.commit()
        res = client.get(f"/api/exports/decks/{deck_id}/cards.csv")
        break
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "id,card_type" in res.text or "id," in res.text


def test_api_export_deck_csv_not_found() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/exports/decks/nonexistent-deck-id/cards.csv")
    assert res.status_code == 404


def test_api_export_deck_csv_deck_id_too_long() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/exports/decks/" + "x" * 81 + "/cards.csv")
    assert res.status_code == 400


# --- Metrics ---


def test_api_metrics_summary() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/metrics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "n" in data
    assert "by_rating" in data
    assert "again_rate" in data


def test_api_metrics_summary_after_answer_shows_data() -> None:
    """Submit an answer then GET metrics/summary; must see n >= 1 (same DB as request)."""
    from app.db import connection
    from app.repositories.cards import CardRepository
    from app.repositories.decks import DeckRepository
    from app.repositories.notes import NoteRepository
    from app.repositories.reviews import ReviewRepository
    from app.repositories.users import UserRepository

    for client, db_path in _test_client_same_db():
        with connection(db_path) as conn:
            user_id = UserRepository(conn).ensure_single_user()
            deck_id = DeckRepository(conn).create_deck(name="MetricsDeck", description="")
            note_id = NoteRepository(conn).upsert_note(source_type="grammar", level="N5", key="m1", fields_json="{}")
            card_id = CardRepository(conn).upsert_card(note_id=note_id, deck_id=deck_id, card_type="grammar_meaning_recognition")
            ReviewRepository(conn).upsert_review_state(card_id=card_id, user_id=user_id, due_at="2020-01-01T00:00:00Z")
            conn.commit()
        start = client.post("/api/sessions/start", json={"deck_id": deck_id})
        assert start.status_code == 200
        session_id = start.json()["session_id"]
        next_res = client.get(f"/api/sessions/{session_id}/next")
        assert next_res.status_code == 200
        next_data = next_res.json()
        if next_data["kind"] == "done":
            pytest.skip("no card in session")
        card_id = next_data["card"]["id"]
        answer = client.post(
            f"/api/sessions/{session_id}/answer",
            json={"card_id": card_id, "rating": "good", "time_ms": 1000},
        )
        assert answer.status_code == 200
        metrics = client.get("/api/metrics/summary")
        assert metrics.status_code == 200
        m = metrics.json()
        assert m["n"] >= 1, "metrics should show at least one answer after submitting (same DB)"
        assert (m.get("by_rating") or {}).get("good", 0) >= 1
        break


# --- TTS ---


def test_api_tts_to_kana() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/tts/to-kana?text=日本語&lang=ja")
    assert res.status_code == 200
    data = res.json()
    assert "kana" in data
    assert len(data["kana"]) >= 1


def test_api_tts_to_kana_empty_text() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/tts/to-kana?text=&lang=ja")
    assert res.status_code == 400


def test_api_tts_to_kana_text_too_long() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/tts/to-kana?text=" + "x" * 501 + "&lang=ja")
    assert res.status_code == 400


def test_api_tts_to_kana_non_ja_passthrough() -> None:
    client = _test_client_with_auth()
    res = client.get("/api/tts/to-kana?text=hello&lang=en")
    assert res.status_code == 200
    assert res.json()["kana"] == "hello"


def test_api_tts_post() -> None:
    """POST /api/tts returns 200 when TTS engine available; 500 when not (no handler)."""
    from unittest.mock import patch

    from app.tts.strategy import TtsResult

    client = _test_client_with_auth()
    # Mock so route runs without requiring espeak; route does not catch RuntimeError so we avoid 500
    with patch("app.routes.tts.TtsService") as mock_svc_cls:
        mock_svc_cls.return_value.synthesize.return_value = TtsResult(
            cache_key="abc12",
            file_path="/tmp/abc12.wav",
            mime_type="audio/wav",
            cache_hit=False,
        )
        res = client.post("/api/tts", json={"text": "test", "lang": "en", "rate": 1.0})
    assert res.status_code == 200
    data = res.json()
    assert "url" in data
    assert data.get("cache_key") == "abc12"


# --- Imports (grammar CSV) ---


def test_api_import_grammar_minimal_csv() -> None:
    client = _test_client_with_auth()
    csv_content = b"japanese_expression,english_meaning\nword,meaning\n"
    res = client.post(
        "/api/imports/grammar",
        data={
            "level": "N5",
            "deck_name": "Imported Grammar",
            "merge_policy": "overwrite",
        },
        files={"file": ("grammar.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["created_notes"] >= 1
    assert data["created_cards"] >= 1


def test_api_import_grammar_level_too_long() -> None:
    client = _test_client_with_auth()
    csv_content = b"japanese_expression,english_meaning\nx,y\n"  # ASCII-only
    res = client.post(
        "/api/imports/grammar",
        data={"level": "x" * 17},
        files={"file": ("g.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 400


def test_api_import_grammar_missing_required_columns() -> None:
    """Grammar import fails when CSV lacks required header columns."""
    client = _test_client_with_auth()
    csv_content = b"a,b\n1,2\n"
    res = client.post(
        "/api/imports/grammar",
        data={"level": "N5"},
        files={"file": ("g.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 400


def test_api_import_grammar_n3_style() -> None:
    """N3-style columns: japanese_expression, english_meaning, grammar_structure, example_1..5."""
    client = _test_client_with_auth()
    csv_content = (
        b"japanese_expression,english_meaning,grammar_structure,example_1,example_2,example_3\n"
        b"ageru,to finish doing,Verb stem + ageru,Ex1 sentence.,Ex2 sentence.,Ex3.\n"
    )
    res = client.post(
        "/api/imports/grammar",
        data={
            "level": "N3",
            "deck_name": "N3 Grammar Import",
            "merge_policy": "overwrite",
        },
        files={"file": ("grammar.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["created_notes"] == 1
    assert data["created_cards"] >= 1


def test_api_import_vocabulary_header_format() -> None:
    """Vocabulary import uses header-based CSV (rank, word, reading_kana, meaning, example_1, ...)."""
    client = _test_client_with_auth()
    csv_content = (
        b"rank,word,reading_kana,reading_romaji,part_of_speech,meaning,example_1,example_2\n"
        b"1,\xe5\xa4\xa7\xe5\x88\x87,\xe3\x81\x9f\xe3\x81\x84\xe3\x81\x9b\xe3\x81\xa4,taisetsu,Adjective,important,ex1 sentence,ex2\n"
    )
    res = client.post(
        "/api/imports/vocabulary",
        data={
            "level": "N5",
            "deck_name": "N5 Vocab Import",
            "merge_policy": "overwrite",
        },
        files={"file": ("vocab.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["created_notes"] == 1
    assert data["created_cards"] >= 1


# --- Imports (sync / reimport) ---


def test_api_sync_import_success() -> None:
    """Create deck with one grammar row, then sync same-format CSV with one existing + one new row."""
    client = _test_client_with_auth()
    csv1 = b"japanese_expression,english_meaning\nword1,meaning1\n"
    res1 = client.post(
        "/api/imports/grammar",
        data={"level": "N5", "deck_name": "Sync Test Deck"},
        files={"file": ("g.csv", io.BytesIO(csv1), "text/csv")},
    )
    assert res1.status_code == 200
    deck_id = res1.json()["deck_id"]
    csv2 = b"japanese_expression,english_meaning\nword1,meaning1\nword2,meaning2\n"
    res2 = client.post(
        "/api/imports/sync",
        data={"deck_id": deck_id, "level": "N5", "source_type": "grammar", "format": "default", "merge_existing": "skip"},
        files={"file": ("g2.csv", io.BytesIO(csv2), "text/csv")},
    )
    assert res2.status_code == 200
    data = res2.json()
    assert data["ok"] is True
    assert data["deck_id"] == deck_id
    assert data["created_notes"] == 1
    assert data["skipped"] == 1
    assert data["created_cards"] >= 1


def test_api_sync_import_deck_not_found() -> None:
    client = _test_client_with_auth()
    csv_content = b"japanese_expression,english_meaning\nx,y\n"
    res = client.post(
        "/api/imports/sync",
        data={"deck_id": "nonexistent-deck-id", "level": "N5", "source_type": "grammar", "format": "default"},
        files={"file": ("g.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res.status_code == 400
    assert "deck" in (res.json().get("detail") or "").lower()


def test_api_sync_import_invalid_source_type() -> None:
    client = _test_client_with_auth()
    res = client.post(
        "/api/imports/sync",
        data={"deck_id": "any", "level": "N5", "source_type": "invalid", "format": "default"},
        files={"file": ("g.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )
    assert res.status_code == 400


def test_api_import_csv_file_too_large_rejected() -> None:
    """CSV uploads over CSV_UPLOAD_MAX_BYTES (from env) are rejected to avoid DoS."""
    one_mib = 1024 * 1024
    old = os.environ.get("CSV_UPLOAD_MAX_BYTES")
    try:
        os.environ["CSV_UPLOAD_MAX_BYTES"] = str(one_mib)
        client = _test_client_with_auth()
        # Upload 1 MiB + 1 byte (over the limit)
        res = client.post(
            "/api/imports/grammar",
            data={"level": "N5", "merge_policy": "overwrite"},
            files={"file": ("big.csv", io.BytesIO(b"x" * (one_mib + 1)), "text/csv")},
        )
        assert res.status_code == 400
        assert "too large" in (res.json().get("detail") or "").lower()
    finally:
        if old is None:
            os.environ.pop("CSV_UPLOAD_MAX_BYTES", None)
        else:
            os.environ["CSV_UPLOAD_MAX_BYTES"] = old
