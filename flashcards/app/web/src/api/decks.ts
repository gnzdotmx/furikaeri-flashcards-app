import { authHeaders } from "./core";
import { LIST_CARDS_LIMIT, SEARCH_RESULTS_LIMIT } from "../constants";

export type Deck = { id: string; name: string; description?: string | null };

export async function fetchDecks(): Promise<Deck[]> {
  const res = await fetch("/api/decks", { headers: authHeaders(), credentials: "include" });
  if (!res.ok) throw new Error(`decks failed: ${res.status}`);
  const body = (await res.json()) as { decks: Deck[] };
  return body.decks;
}

export async function deleteDeck(deckId: string): Promise<{ deck_id: string; deleted: boolean }> {
  const res = await fetch(`/api/decks/${encodeURIComponent(deckId)}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  const body = await res.json();
  if (!res.ok) throw new Error((body as { detail?: string })?.detail ?? `delete deck failed: ${res.status}`);
  return body as { deck_id: string; deleted: boolean };
}

export type DeckCardsResponse = {
  cards: Array<{
    id: string;
    note_id: string;
    deck_id: string;
    card_type: string;
    front_template?: string | null;
    back_template?: string | null;
    tags_json?: string | null;
    created_at: string;
  }>;
  counts_by_type: Record<string, number>;
};

export async function fetchDeckCards(deckId: string): Promise<DeckCardsResponse> {
  const res = await fetch(`/api/decks/${encodeURIComponent(deckId)}/cards?limit=${LIST_CARDS_LIMIT}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`deck cards failed: ${res.status}`);
  return (await res.json()) as DeckCardsResponse;
}

export type LeechCard = {
  id: string;
  note_id: string;
  deck_id: string;
  card_type: string;
  front_template?: string | null;
  back_template?: string | null;
  tags_json?: string | null;
  created_at: string;
  lapses: number;
  leech_flag: number;
  suspended: number;
};

export type DeckLeechesResponse = {
  leeches: LeechCard[];
  deck_id: string;
  deck_name: string;
};

export async function fetchDeckLeeches(deckId: string): Promise<DeckLeechesResponse> {
  const res = await fetch(`/api/decks/${encodeURIComponent(deckId)}/leeches?limit=${LIST_CARDS_LIMIT}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`leeches failed: ${res.status}`);
  return (await res.json()) as DeckLeechesResponse;
}

export type DeckLabelsResponse = {
  deck_id: string;
  labels: string[];
};

export async function fetchDeckLabels(deckId: string): Promise<DeckLabelsResponse> {
  const res = await fetch(`/api/decks/${encodeURIComponent(deckId)}/labels`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`labels failed: ${res.status}`);
  return (await res.json()) as DeckLabelsResponse;
}

export async function setCardSuspended(cardId: string, suspended: boolean): Promise<{ card_id: string; suspended: boolean }> {
  const res = await fetch(`/api/cards/${encodeURIComponent(cardId)}/suspend`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ suspended }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error((body as { detail?: string })?.detail ?? `suspend failed: ${res.status}`);
  return body as { card_id: string; suspended: boolean };
}

export type SearchExamplesCard = {
  id: string;
  note_id: string;
  deck_id: string;
  card_type: string;
  front_template?: string | null;
  back_template?: string | null;
  tags_json?: string | null;
  created_at: string;
  deck_name?: string;
};

export type SearchExamplesResponse = {
  cards: SearchExamplesCard[];
  query: string;
};

export async function fetchSearchExamples(query: string, limit = SEARCH_RESULTS_LIMIT): Promise<SearchExamplesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (query.trim()) params.set("q", query.trim());
  const res = await fetch(`/api/search/examples?${params.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`search failed: ${res.status}`);
  return (await res.json()) as SearchExamplesResponse;
}
