"""Decks, cards, notes, leeches, search."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from ..auth import get_current_user_id
from ..db import connection
from ..repositories.decks import DeckRepository
from ..repositories.notes import NoteRepository
from ..repositories.reviews import ReviewRepository
from ..settings import Settings, get_settings
from ..study_config import get_study_config
from ..exports.deck_export import export_deck_csv

from .dependencies import get_sqlite_path

router = APIRouter()


@router.get("/decks")
def list_decks(settings: Settings = Depends(get_settings)):
    with connection(settings.sqlite_path) as conn:
        decks = DeckRepository(conn)
        return {"decks": decks.list_decks()}


@router.get("/decks/{deck_id}/cards")
def list_deck_cards(deck_id: str, limit: int | None = None, settings: Settings = Depends(get_settings)):
    if limit is None:
        limit = get_study_config().limits.list_cards_limit
    if len(deck_id) > 80:
        raise HTTPException(status_code=400, detail="deck_id too long")
    with connection(settings.sqlite_path) as conn:
        from ..repositories.cards import CardRepository

        cards = CardRepository(conn)
        items = cards.list_cards_for_deck(deck_id, limit=int(limit))
        counts: dict[str, int] = {}
        for c in items:
            ct = c.get("card_type") or "unknown"
            counts[ct] = counts.get(ct, 0) + 1
        return {"cards": items, "counts_by_type": counts}


@router.get("/decks/{deck_id}/leeches")
def list_deck_leeches(
    deck_id: str,
    user_id: str = Depends(get_current_user_id),
    limit: int | None = None,
    settings: Settings = Depends(get_settings),
):
    """Leeches for this deck (current user)."""
    if limit is None:
        limit = get_study_config().limits.list_cards_limit
    if len(deck_id) > 80:
        raise HTTPException(status_code=400, detail="deck_id too long")
    with connection(settings.sqlite_path) as conn:
        deck = DeckRepository(conn).get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="deck not found")
        from ..repositories.cards import CardRepository

        cards = CardRepository(conn)
        leeches = cards.get_leeches(deck_id=deck_id, user_id=user_id, limit=int(limit))
        return {"leeches": leeches, "deck_id": deck_id, "deck_name": deck["name"]}


@router.get("/decks/{deck_id}/labels")
def list_deck_labels(
    deck_id: str,
    settings: Settings = Depends(get_settings),
):
    """Distinct label tags for this deck (study filters)."""
    if len(deck_id) > 80:
        raise HTTPException(status_code=400, detail="deck_id too long")
    with connection(settings.sqlite_path) as conn:
        deck = DeckRepository(conn).get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="deck not found")
        from ..repositories.cards import CardRepository

        cards = CardRepository(conn)
        lim = get_study_config().limits.list_cards_limit
        labels = cards.list_labels_for_deck(deck_id, limit=int(lim))
        return {"deck_id": deck_id, "labels": labels}


class CardSuspendReq(BaseModel):
    suspended: bool = True


@router.post("/cards/{card_id}/suspend")
def set_card_suspended(
    card_id: str,
    req: CardSuspendReq,
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    """Suspend or unsuspend a card (exclude or include in study sessions)."""
    if len(card_id) > 80:
        raise HTTPException(status_code=400, detail="card_id too long")
    with connection(settings.sqlite_path) as conn:
        reviews = ReviewRepository(conn)
        updated = reviews.set_suspended(card_id=card_id, user_id=user_id, suspended=req.suspended)
        if not updated:
            raise HTTPException(status_code=404, detail="card or review state not found")
        return {"card_id": card_id, "suspended": req.suspended}


@router.get("/search/examples")
def search_examples(q: str = "", limit: int | None = None, settings: Settings = Depends(get_settings)):
    """Search cards by word; matches front/back template text."""
    lim_cfg = get_study_config().limits
    limit = int(limit) if limit is not None else lim_cfg.search_examples_limit
    limit = max(1, min(limit, lim_cfg.search_examples_max))
    q = (q or "").strip()
    with connection(settings.sqlite_path) as conn:
        from ..repositories.cards import CardRepository

        cards = CardRepository(conn)
        items = cards.search_cards_by_text(q, limit=limit)
    return {"cards": items, "query": q}


@router.get("/notes")
def list_notes(
    source_type: str | None = None,
    level: str | None = None,
    limit: int | None = None,
    settings: Settings = Depends(get_settings),
):
    if source_type and source_type not in ("grammar", "kanji", "vocabulary"):
        raise HTTPException(status_code=400, detail="invalid source_type")
    if level and len(level) > 16:
        raise HTTPException(status_code=400, detail="invalid level")
    if limit is None:
        limit = get_study_config().limits.list_cards_limit
    with connection(settings.sqlite_path) as conn:
        notes = NoteRepository(conn)
        return {"notes": notes.list_notes(source_type=source_type, level=level, limit=int(limit))}


@router.get("/exports/decks/{deck_id}/cards.csv")
def export_deck_cards_csv(request: Request, deck_id: str, sqlite_path: str = Depends(get_sqlite_path)):
    if len(deck_id) > 80:
        raise HTTPException(status_code=400, detail="deck_id too long")
    with connection(sqlite_path) as conn:
        deck = DeckRepository(conn).get_deck(deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="deck not found")
        csv_text, _ = export_deck_csv(conn, deck_id)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="deck_{deck_id}_cards.csv"'},
    )
