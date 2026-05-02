import { authHeaders } from "./core";

export type CardStudyNoteResponse = {
  card_id: string;
  body: string | null;
  updated_at: string | null;
};

export async function fetchCardStudyNote(cardId: string): Promise<CardStudyNoteResponse> {
  const res = await fetch(`/api/cards/${encodeURIComponent(cardId)}/study-note`, {
    headers: authHeaders(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string })?.detail ?? `fetch study note failed: ${res.status}`);
  return data as CardStudyNoteResponse;
}

export async function putCardStudyNote(cardId: string, body: string): Promise<CardStudyNoteResponse> {
  const res = await fetch(`/api/cards/${encodeURIComponent(cardId)}/study-note`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ body }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string })?.detail ?? `save study note failed: ${res.status}`);
  return data as CardStudyNoteResponse;
}

export async function deleteCardStudyNote(cardId: string): Promise<void> {
  const res = await fetch(`/api/cards/${encodeURIComponent(cardId)}/study-note`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.status === 404) return;
  if (res.ok) return;
  const data = await res.json().catch(() => ({}));
  throw new Error((data as { detail?: string })?.detail ?? `delete study note failed: ${res.status}`);
}
