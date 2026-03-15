import { authHeaders, isDev } from "./core";

export type SessionStartResponse = {
  session_id: string;
  deck: { id: string; name: string };
  due_now: number;
  due_today: number;
  new_available: number;
  new_limit: number;
  estimated_minutes: number;
  leech_count?: number;
  daily_goal_reviews?: number | null;
  reviews_done_today?: number;
  streak_days?: number;
};

export async function startSession(
  deckId: string,
  options?: { catch_up?: boolean; include_listening?: boolean }
): Promise<SessionStartResponse> {
  const res = await fetch("/api/sessions/start", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      deck_id: deckId,
      mode: "mixed",
      ...(options?.catch_up === true && { catch_up: true }),
      ...(options?.include_listening === false && { include_listening: false }),
    }),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `start session failed: ${res.status}`);
  return body as SessionStartResponse;
}

export type SessionCard = {
  id: string;
  note_id: string;
  deck_id: string;
  card_type: string;
  front_template?: string | null;
  back_template?: string | null;
  tags_json?: string | null;
  created_at: string;
  due_at?: string;
  stability?: number;
  difficulty?: number;
  lapses?: number;
  reps?: number;
  avg_time_ms?: number;
  streak?: number;
  leech_flag?: number;
};

export type NextCardResponse =
  | { kind: "done" }
  | {
      kind: "due" | "new" | "learning";
      new_remaining: number;
      card: SessionCard;
      presentation_defaults?: { furigana_mode?: string };
    };

export async function nextCard(sessionId: string, options?: { label?: string | null }): Promise<NextCardResponse> {
  const params = new URLSearchParams();
  if (options?.label && options.label.trim()) {
    params.set("label", options.label.trim());
  }
  const qs = params.toString();
  const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/next${qs ? `?${params.toString()}` : ""}`, {
    headers: authHeaders(),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `next failed: ${res.status}`);
  return body as NextCardResponse;
}

export type AnswerCardResponse = {
  ok?: boolean;
  card_id: string;
  rating: string;
  next_due_at?: string;
  stability?: number;
  difficulty?: number;
  answer_submitted_total?: number;
  [key: string]: unknown;
};

export async function answerCard(
  sessionId: string,
  cardId: string,
  rating: "again" | "hard" | "good" | "easy",
  timeMs: number,
  hintsUsed: number,
): Promise<AnswerCardResponse> {
  const url = `/api/sessions/${encodeURIComponent(sessionId)}/answer`;
  const body = { card_id: cardId, rating, time_ms: timeMs, hints_used: hintsUsed };
  if (isDev() && typeof window !== "undefined" && typeof console.debug === "function") {
    console.debug("[answerCard] POST", url, body);
  }
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error((data as { detail?: string })?.detail ?? `answer failed: ${res.status}`);
  if (isDev() && typeof window !== "undefined" && typeof console.debug === "function") {
    console.debug("[answerCard] OK", res.status, data);
  }
  return data as AnswerCardResponse;
}
