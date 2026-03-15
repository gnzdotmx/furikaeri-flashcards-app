from __future__ import annotations

import json
import uuid
from dataclasses import dataclass


# Stable namespace UUID for deterministic card IDs.
CARD_ID_NAMESPACE = uuid.UUID("3b4c2b2d-6a7a-4d4d-9f6d-0b8f3a9b0e5a")


class CardType:
    # Grammar
    GRAMMAR_MEANING_RECOGNITION = "grammar_meaning_recognition"
    GRAMMAR_STRUCTURE_PRODUCTION = "grammar_structure_production"
    GRAMMAR_CLOZE = "grammar_cloze"

    # Kanji
    KANJI_READING_RECALL = "kanji_reading_recall"
    KANJI_MEANING_RECALL = "kanji_meaning_recall"
    KANJI_USAGE = "kanji_usage"

    # Vocabulary
    VOCAB_MEANING_RECALL = "vocab_meaning_recall"
    VOCAB_READING_RECALL = "vocab_reading_recall"
    VOCAB_LISTENING = "vocab_listening"


@dataclass(frozen=True)
class CardSpec:
    """Generated card to persist; front/back are JSON-serializable dicts."""

    card_id: str
    card_type: str
    tags: list[str]
    front: dict
    back: dict


def stable_card_id(*parts: str) -> str:
    """Deterministic UUIDv5 from parts (keep inputs stable across imports)."""
    name = "|".join(parts)
    return str(uuid.uuid5(CARD_ID_NAMESPACE, name))


def json_dumps(obj: dict | list) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

