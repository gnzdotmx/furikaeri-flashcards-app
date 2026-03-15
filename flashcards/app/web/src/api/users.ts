import { authHeaders } from "./core";

export type UserSettingsResponse = {
  new_cards_per_day: number;
  target_retention: number;
  daily_goal_reviews: number | null;
};

export async function fetchUserSettings(): Promise<UserSettingsResponse> {
  const res = await fetch("/api/users/settings", { headers: authHeaders() });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `user settings failed: ${res.status}`);
  return body as UserSettingsResponse;
}

export async function updateUserSettings(patch: { daily_goal_reviews?: number | null }): Promise<{ daily_goal_reviews: number | null }> {
  const res = await fetch("/api/users/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(patch),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `user settings update failed: ${res.status}`);
  return body as { daily_goal_reviews: number | null };
}
