from __future__ import annotations

from typing import Any

from ..imports.utils import norm_text
from .types import CardSpec, CardType, stable_card_id


def _tags_base(source_type: str, level: str, card_type: str) -> list[str]:
    return [f"source:{source_type}", f"level:{level}", f"type:{card_type}"]


def _first_example(examples: list[str] | None) -> str:
    if not examples:
        return ""
    for ex in examples:
        if isinstance(ex, str) and ex.strip():
            return ex.strip()
    return ""


def _first_example_line_for_display(examples: list[str] | None, min_chars: int = 5) -> str:
    """First line of the first example whose first line has at least min_chars.
    Skips fragment-only first lines (e.g. 'いる。') so card fronts show a real sentence or nothing."""
    if not examples:
        return ""
    for ex in examples:
        if not isinstance(ex, str) or not ex.strip():
            continue
        first_line = (ex.split("\n")[0] or "").strip()
        if first_line and len(first_line) >= min_chars:
            return first_line
    return ""


def _split_example(example_block: str) -> dict[str, str]:
    """Split multiline example into jp, romaji, en."""
    lines = [line.strip() for line in (example_block or "").split("\n") if line.strip()]
    out = {"jp": "", "romaji": "", "en": ""}
    if not lines:
        return out
    out["jp"] = lines[0]
    if len(lines) >= 2:
        out["romaji"] = lines[1]
    if len(lines) >= 3:
        out["en"] = lines[2]
    return out


class CardFactory:
    """Generate CardSpecs from a note's fields dict."""

    def generate_for_note(
        self,
        *,
        deck_name: str,
        source_type: str,
        level: str,
        note_key: str,
        fields: dict[str, Any],
    ) -> list[CardSpec]:
        deck_name = norm_text(deck_name)
        level = norm_text(level)
        note_key = norm_text(note_key)

        if source_type == "grammar":
            return self._grammar(deck_name=deck_name, level=level, note_key=note_key, fields=fields)
        if source_type == "kanji":
            return self._kanji(deck_name=deck_name, level=level, note_key=note_key, fields=fields)
        if source_type == "vocabulary":
            return self._vocab(deck_name=deck_name, level=level, note_key=note_key, fields=fields)
        return []

    def _grammar(self, *, deck_name: str, level: str, note_key: str, fields: dict[str, Any]) -> list[CardSpec]:
        expr = norm_text(str(fields.get("japanese_expression", note_key)))
        meaning = norm_text(str(fields.get("english_meaning", "")))
        structure = str(fields.get("grammar_structure", "") or "").strip()
        examples = fields.get("examples") if isinstance(fields.get("examples"), list) else []
        ex0 = _first_example(examples)

        # Single card per grammar point: front = example only, back = meaning + structure + examples
        ct = CardType.GRAMMAR_MEANING_RECOGNITION
        return [
            CardSpec(
                card_id=stable_card_id(deck_name, "grammar", level, expr, ct),
                card_type=ct,
                tags=_tags_base("grammar", level, ct),
                front={"expression": expr, "example": ex0},
                back={"meaning": meaning, "structure": structure, "examples": examples[:5], "expression": expr},
            )
        ]

    def _kanji(self, *, deck_name: str, level: str, note_key: str, fields: dict[str, Any]) -> list[CardSpec]:
        kanji = (fields.get("kanji") or note_key or "").strip()
        meaning = norm_text(str(fields.get("meaning", "")))
        onyomi = str(fields.get("onyomi", "") or "").strip()
        kunyomi = str(fields.get("kunyomi", "") or "").strip()
        examples = fields.get("examples") if isinstance(fields.get("examples"), list) else []
        ex0 = _first_example(examples)
        ex0_parts = _split_example(ex0)

        specs: list[CardSpec] = []

        ct = CardType.KANJI_READING_RECALL
        specs.append(
            CardSpec(
                card_id=stable_card_id(deck_name, "kanji", level, kanji, ct),
                card_type=ct,
                tags=_tags_base("kanji", level, ct),
                front={"kanji": kanji, "prompt": "Recall readings (onyomi/kunyomi)."},
                back={"onyomi": onyomi, "kunyomi": kunyomi, "meaning": meaning, "examples": examples[:5]},
            )
        )

        ct = CardType.KANJI_MEANING_RECALL
        specs.append(
            CardSpec(
                card_id=stable_card_id(deck_name, "kanji", level, kanji, ct),
                card_type=ct,
                tags=_tags_base("kanji", level, ct),
                front={"kanji": kanji, "prompt": "Recall meaning."},
                back={"meaning": meaning, "onyomi": onyomi, "kunyomi": kunyomi, "examples": examples[:5]},
            )
        )

        # Optional usage card if we have an example sentence.
        if ex0_parts.get("jp"):
            ct = CardType.KANJI_USAGE
            specs.append(
                CardSpec(
                    card_id=stable_card_id(deck_name, "kanji", level, kanji, ct),
                    card_type=ct,
                    tags=_tags_base("kanji", level, ct) + ["mode:usage"],
                    front={
                        "prompt": "Read and understand the sentence.",
                        "sentence_jp": ex0_parts["jp"],
                        "target": kanji,
                    },
                    back={"sentence_en": ex0_parts.get("en", ""), "sentence_romaji": ex0_parts.get("romaji", ""), "meaning": meaning},
                )
            )

        return specs

    def _vocab(self, *, deck_name: str, level: str, note_key: str, fields: dict[str, Any]) -> list[CardSpec]:
        # Vocabulary note fields (header-based CSV: word, reading_kana, meaning, examples, etc.).
        word = (fields.get("word") or fields.get("kanji_word") or "").strip()
        if not word:
            word = note_key.split("|", 1)[0].strip()
        meaning = norm_text(str(fields.get("meaning", fields.get("english_word", "")) or ""))
        reading_kana = (fields.get("reading_kana") or fields.get("hiragana_word") or "").strip()
        pos = (fields.get("part_of_speech") or "").strip()
        examples = fields.get("examples") if isinstance(fields.get("examples"), list) else []
        examples_capped = (examples or [])[:5]
        # Use first substantial example line on front (skip fragment-only lines like "いる。")
        ex0_display = _first_example_line_for_display(examples)
        # Never show rank: if word or pos is purely numeric, use reading/note_key or clear pos
        if word.isdigit():
            word = reading_kana or note_key.split("|", 1)[0].strip()
        if pos.isdigit():
            pos = ""

        # Optional labels field -> label:* tags
        labels_field = fields.get("labels")
        if isinstance(labels_field, list):
            labels_src = labels_field
        elif labels_field:
            labels_src = str(labels_field).split(",")
        else:
            labels_src = []
        label_tags = [f"label:{norm_text(str(lb))}" for lb in labels_src if str(lb).strip()]
        # Never put "rank" in front/back templates
        # Front: word at top, first example below (same structure as grammar). Back: word, reading, meaning, examples.
        back_base: dict[str, Any] = {
            "word": word,
            "reading_kana": reading_kana,
            "meaning": meaning,
            "examples": examples_capped,
        }
        front_base: dict[str, Any] = {
            "word": word,
            "reading_kana": reading_kana,
            "pos": pos,
            "example": ex0_display,
        }

        specs: list[CardSpec] = []

        ct = CardType.VOCAB_MEANING_RECALL
        specs.append(
            CardSpec(
                card_id=stable_card_id(deck_name, "vocabulary", level, f"{word}|{reading_kana}|{meaning}", ct),
                card_type=ct,
                tags=_tags_base("vocabulary", level, ct)
                + ([f"pos:{pos.split(',')[0].strip()}"] if pos else [])
                + label_tags,
                front={**front_base, "prompt": "Recall meaning."},
                back=dict(back_base),
            )
        )

        ct = CardType.VOCAB_READING_RECALL
        specs.append(
            CardSpec(
                card_id=stable_card_id(deck_name, "vocabulary", level, f"{word}|{reading_kana}|{meaning}", ct),
                card_type=ct,
                tags=_tags_base("vocabulary", level, ct)
                + ([f"pos:{pos.split(',')[0].strip()}"] if pos else [])
                + label_tags,
                front={**front_base, "prompt": "Recall reading (kana)."},
                back=dict(back_base),
            )
        )

        # No vocab_listening cards: user can use the Play button on meaning/reading cards for TTS.

        return specs

