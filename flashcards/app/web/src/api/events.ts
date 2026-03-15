import { authHeaders } from "./core";

export async function logEvent(
  eventType: "hint_toggled" | "audio_played" | "reveal_toggled",
  payload: Record<string, unknown>,
): Promise<void> {
  const res = await fetch("/api/events", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ event_type: eventType, ...payload }),
  });
  if (!res.ok) {
    return;
  }
}
