import json
import logging

from ..cards.factory import CardFactory
from ..cards.types import json_dumps
from ..repositories.cards import CardRepository
from ..repositories.decks import DeckRepository
from ..repositories.notes import NoteRepository
from .adapters import ImportItem, encode_fields_json
from .utils import norm_text

logger = logging.getLogger(__name__)


def _merge_examples(existing_fields: dict, new_fields: dict) -> dict:
    """Merge examples arrays, dedupe, keep order."""
    out = dict(existing_fields)
    new = dict(new_fields)

    ex1 = existing_fields.get("examples") if isinstance(existing_fields.get("examples"), list) else []
    ex2 = new_fields.get("examples") if isinstance(new_fields.get("examples"), list) else []

    seen = set()
    merged = []
    for ex in list(ex1) + list(ex2):
        if not isinstance(ex, str):
            continue
        k = ex.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        merged.append(ex)

    out.update(new)
    if merged:
        out["examples"] = merged
    return out


def _unique_key(notes: NoteRepository, *, source_type: str, level: str, base_key: str) -> str:
    """Unique key for keep_both: base_key or "base_key (2)", etc."""
    base_key = norm_text(base_key)
    if not notes.get_note_by_key(source_type=source_type, level=level, key=base_key):
        return base_key
    n = 2
    while True:
        k = f"{base_key} ({n})"
        if not notes.get_note_by_key(source_type=source_type, level=level, key=k):
            return k
        n += 1


def import_items_into_deck(
    *,
    conn,
    level: str,
    deck_name: str,
    source_type: str,
    items: list[ImportItem],
    merge_policy: str,
) -> dict:
    """Import items into deck; merge_policy: keep_both | overwrite | merge_examples."""
    deck_name = norm_text(deck_name)
    level = norm_text(level)
    if not deck_name or len(deck_name) > 120:
        raise ValueError("deck_name invalid or too long")
    if not level or len(level) > 16:
        raise ValueError("level invalid or too long")

    if merge_policy not in ("keep_both", "overwrite", "merge_examples"):
        raise ValueError("merge_policy must be keep_both|overwrite|merge_examples")

    decks = DeckRepository(conn)
    notes = NoteRepository(conn)
    cards = CardRepository(conn)
    factory = CardFactory()

    deck_id = decks.create_deck(name=deck_name, description=f"Imported {source_type} ({level})")

    created_notes = 0
    created_cards = 0
    updated_notes = 0
    deleted_placeholders = 0
    deleted_obsolete_cards = 0

    for item in items:
        key = norm_text(item.key)
        if merge_policy == "keep_both":
            key = _unique_key(notes, source_type=item.source_type, level=item.level, base_key=key)

        existing = notes.get_note_by_key(source_type=item.source_type, level=item.level, key=key)
        fields = item.fields
        source_url = item.source_url

        if existing and merge_policy == "merge_examples":
            try:
                existing_fields = json.loads(existing["fields_json"])
                fields = _merge_examples(existing_fields, fields)
            except Exception:
                logger.warning(
                    "Merge examples failed for note (using new fields)",
                    extra={"source_type": item.source_type, "level": item.level},
                )

        note_id = notes.upsert_note(
            source_type=item.source_type,
            level=item.level,
            key=key,
            fields_json=encode_fields_json(fields),
            source_url=source_url,
        )

        if existing:
            updated_notes += 1
        else:
            created_notes += 1

        # Generate real study cards (Phase 3) and upsert them deterministically.
        specs = factory.generate_for_note(
            deck_name=deck_name,
            source_type=item.source_type,
            level=item.level,
            note_key=key,
            fields=fields,
        )
        keep_card_types = {s.card_type for s in specs}
        for spec in specs:
            cards.upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type=spec.card_type,
                card_id=spec.card_id,
                front_template=json_dumps(spec.front),
                back_template=json_dumps(spec.back),
                tags_json=json_dumps(spec.tags),
            )
            created_cards += 1
        # Remove any cards for this note that we no longer generate (e.g. old grammar card types).
        n_obsolete = cards.delete_cards_for_note_except_types(
            note_id=note_id, deck_id=deck_id, keep_card_types=keep_card_types
        )
        deleted_obsolete_cards += n_obsolete
        deleted_placeholders += cards.delete_placeholders_for_note(note_id=note_id, deck_id=deck_id)

    return {
        "deck_id": deck_id,
        "deck_name": deck_name,
        "level": level,
        "source_type": source_type,
        "created_notes": created_notes,
        "updated_notes": updated_notes,
        "created_cards": created_cards,
        "deleted_placeholders": deleted_placeholders,
        "deleted_obsolete_cards": deleted_obsolete_cards,
    }


def sync_items_into_deck(
    *,
    conn,
    deck_id: str,
    level: str,
    source_type: str,
    items: list[ImportItem],
    merge_existing: str = "skip",  # skip | merge_examples
) -> dict:
    """Sync items into existing deck; merge_existing: skip | merge_examples."""
    level = norm_text(level)
    if not level or len(level) > 16:
        raise ValueError("level invalid or too long")
    if source_type not in ("grammar", "kanji", "vocabulary"):
        raise ValueError("source_type must be grammar|kanji|vocabulary")
    if merge_existing not in ("skip", "merge_examples"):
        raise ValueError("merge_existing must be skip|merge_examples")

    decks = DeckRepository(conn)
    deck = decks.get_deck(deck_id)
    if not deck:
        raise ValueError("deck not found")
    deck_name = deck["name"]

    notes = NoteRepository(conn)
    cards = CardRepository(conn)
    factory = CardFactory()

    created_notes = 0
    created_cards = 0
    updated_notes = 0
    skipped = 0
    deleted_placeholders = 0
    deleted_obsolete_cards = 0

    for item in items:
        key = norm_text(item.key)
        existing = notes.get_note_by_key(source_type=item.source_type, level=item.level, key=key)
        if existing:
            if merge_existing == "skip":
                skipped += 1
                continue
            # merge_examples: merge examples and upsert
            try:
                existing_fields = json.loads(existing["fields_json"])
                fields = _merge_examples(existing_fields, item.fields)
            except Exception:
                logger.warning(
                    "Sync merge examples failed for note (using new fields)",
                    extra={"source_type": item.source_type, "level": item.level},
                )
                fields = item.fields
            source_url = item.source_url or existing.get("source_url")
        else:
            fields = item.fields
            source_url = item.source_url

        note_id = notes.upsert_note(
            source_type=item.source_type,
            level=item.level,
            key=key,
            fields_json=encode_fields_json(fields),
            source_url=source_url,
        )

        if existing:
            updated_notes += 1
        else:
            created_notes += 1

        specs = factory.generate_for_note(
            deck_name=deck_name,
            source_type=item.source_type,
            level=item.level,
            note_key=key,
            fields=fields,
        )
        keep_card_types = {s.card_type for s in specs}
        for spec in specs:
            cards.upsert_card(
                note_id=note_id,
                deck_id=deck_id,
                card_type=spec.card_type,
                card_id=spec.card_id,
                front_template=json_dumps(spec.front),
                back_template=json_dumps(spec.back),
                tags_json=json_dumps(spec.tags),
            )
            created_cards += 1
        n_obsolete = cards.delete_cards_for_note_except_types(
            note_id=note_id, deck_id=deck_id, keep_card_types=keep_card_types
        )
        deleted_obsolete_cards += n_obsolete
        deleted_placeholders += cards.delete_placeholders_for_note(note_id=note_id, deck_id=deck_id)

    return {
        "deck_id": deck_id,
        "deck_name": deck_name,
        "level": level,
        "source_type": source_type,
        "created_notes": created_notes,
        "updated_notes": updated_notes,
        "skipped": skipped,
        "created_cards": created_cards,
        "deleted_placeholders": deleted_placeholders,
        "deleted_obsolete_cards": deleted_obsolete_cards,
    }

