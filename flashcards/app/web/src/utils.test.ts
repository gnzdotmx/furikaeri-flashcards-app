import { describe, expect, it } from "vitest";
import { safeJson, deckLevel, deckSourceType, leechCardSummary } from "./utils";
import type { LeechCard } from "./api";
import { LEECH_LAPSES_THRESHOLD } from "./constants";

describe("safeJson", () => {
  it("parses valid JSON", () => {
    expect(safeJson<{ a: number }>('{"a":1}')).toEqual({ a: 1 });
  });

  it("returns null for empty string", () => {
    expect(safeJson<object>("")).toBeNull();
    expect(safeJson<object>("   ")).toBeNull();
  });

  it("returns null for invalid JSON", () => {
    expect(safeJson<object>("not json")).toBeNull();
  });

  it("returns null for non-string input (never throws)", () => {
    expect(safeJson<object>(null)).toBeNull();
    expect(safeJson<object>(undefined)).toBeNull();
    expect(safeJson<object>(42)).toBeNull();
    expect(safeJson<object>({})).toBeNull();
    expect(safeJson<object>(true)).toBeNull();
  });
});

describe("deckLevel", () => {
  it("extracts level from deck name", () => {
    expect(deckLevel({ id: "1", name: "N3 Grammar" })).toBe("N3");
    expect(deckLevel({ id: "1", name: "N5 Vocabulary" })).toBe("N5");
  });

  it("extracts level from description", () => {
    expect(deckLevel({ id: "1", name: "Deck", description: "Imported (N2)" })).toBe("N2");
  });

  it("extracts custom level from description", () => {
    expect(deckLevel({ id: "1", name: "Deck", description: "Imported vocabulary (custom)" })).toBe("custom");
    expect(deckLevel({ id: "1", name: "Deck", description: "imported grammar (CUSTOM)" })).toBe("custom");
  });

  it("returns null when no level found", () => {
    expect(deckLevel({ id: "1", name: "Custom Deck" })).toBeNull();
  });
});

describe("deckSourceType", () => {
  it("returns kanji for kanji deck", () => {
    expect(deckSourceType({ id: "1", name: "N3 Kanji" })).toBe("kanji");
  });

  it("returns vocabulary for vocab deck", () => {
    expect(deckSourceType({ id: "1", name: "N5 Vocabulary" })).toBe("vocabulary");
  });

  it("returns grammar for grammar deck", () => {
    expect(deckSourceType({ id: "1", name: "N4 Grammar" })).toBe("grammar");
  });

  it("defaults to grammar", () => {
    expect(deckSourceType({ id: "1", name: "Other" })).toBe("grammar");
  });
});

describe("leechCardSummary", () => {
  it("returns summary and searchQuery from grammar card", () => {
    const card: LeechCard = {
      id: "c1",
      note_id: "n1",
      deck_id: "d1",
      card_type: "grammar_meaning_recognition",
      front_template: JSON.stringify({ expression: "だ" }),
      back_template: JSON.stringify({ meaning: "copula" }),
      created_at: "2024-01-01",
      lapses: LEECH_LAPSES_THRESHOLD,
      leech_flag: 1,
      suspended: 0,
    };
    const { summary, searchQuery } = leechCardSummary(card);
    expect(summary).toContain("だ");
    expect(searchQuery).toContain("だ");
  });

  it("returns summary from vocab card", () => {
    const card: LeechCard = {
      id: "c1",
      note_id: "n1",
      deck_id: "d1",
      card_type: "vocab_meaning_recall",
      front_template: JSON.stringify({ word: "日" }),
      back_template: JSON.stringify({ meaning: "day" }),
      created_at: "2024-01-01",
      lapses: LEECH_LAPSES_THRESHOLD,
      leech_flag: 1,
      suspended: 0,
    };
    const { summary, searchQuery } = leechCardSummary(card);
    expect(summary).toContain("日");
    expect(searchQuery).toBeDefined();
  });
});
