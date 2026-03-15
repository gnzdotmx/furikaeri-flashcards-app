import type { Deck } from "./api";
import type { LeechCard } from "./api";
import type { SyncSourceType } from "./api";

/** Parse JSON safely. Returns null for non-string, empty, or invalid JSON (never throws). */
export function safeJson<T>(s: unknown): T | null {
  if (typeof s !== "string" || !s.trim()) return null;
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

/** Derive JLPT level from deck name (e.g. "N3 Grammar") or description (e.g. "Imported grammar (N3)"). */
export function deckLevel(d: Deck): string | null {
  const name = (d.name || "").trim();
  const desc = (d.description ?? "").trim();
  const fromName = name.match(/^(N[1-5])\b/);
  if (fromName) return fromName[1];
  const fromDesc = desc.match(/\((N[1-5])\)/i);
  if (fromDesc) return fromDesc[1];
  if (desc.toLowerCase().includes("(custom)")) {
    return "custom";
  }
  return null;
}

/** Infer import type from deck name/description (e.g. "N3 Kanji" → kanji). */
export function deckSourceType(d: Deck): SyncSourceType {
  const name = (d.name || "").toLowerCase();
  const desc = (d.description ?? "").toLowerCase();
  const combined = `${name} ${desc}`;
  if (combined.includes("kanji")) return "kanji";
  if (combined.includes("vocabulary") || combined.includes("vocab")) return "vocabulary";
  if (combined.includes("grammar")) return "grammar";
  return "grammar";
}

/** Short summary and search query from a leech card's front/back templates. */
export function leechCardSummary(card: LeechCard): { summary: string; searchQuery: string } {
  const front = safeJson<Record<string, unknown>>(card.front_template) ?? {};
  const back = safeJson<Record<string, unknown>>(card.back_template) ?? {};
  const expr = String(front.expression ?? back.expression ?? "").trim();
  const word = String(front.word ?? back.word ?? "").trim();
  const meaning = String(front.meaning ?? back.meaning ?? "").trim();
  const kanji = String(front.kanji ?? back.kanji ?? "").trim();
  const exampleStr = typeof front.example === "string" ? front.example.split("\n")[0] ?? "" : "";
  const part: string = expr || word || kanji || meaning || exampleStr.slice(0, 40) || String(card.card_type ?? "");
  const summary = part.length > 60 ? `${part.slice(0, 57)}…` : part;
  const searchQuery = (expr || word || kanji || meaning.slice(0, 30) || part.slice(0, 30)).trim() || part.slice(0, 30);
  return { summary, searchQuery };
}
