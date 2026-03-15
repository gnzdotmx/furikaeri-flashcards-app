import { authHeaders } from "./core";
import { METRICS_SUMMARY_LIMIT } from "../constants";

export type MetricsResponse = {
  n: number;
  by_rating: { again: number; hard: number; good: number; easy: number };
  again_rate: number;
  retention_proxy: number;
  avg_time_ms: number;
  daily_goal_reviews?: number | null;
  reviews_done_today?: number;
  streak_days?: number;
};

export async function fetchMetrics(): Promise<MetricsResponse> {
  const res = await fetch(`/api/metrics/summary?limit=${METRICS_SUMMARY_LIMIT}`, {
    headers: authHeaders(),
  });
  const ct = res.headers.get("content-type") ?? "";
  let body: Record<string, unknown> | null = null;
  try {
    const text = await res.text();
    if (text && text.trim()) {
      if (ct.includes("application/json")) {
        body = JSON.parse(text);
      } else {
        if (res.ok) body = JSON.parse(text);
      }
    }
  } catch {
    // non-JSON or empty body
  }
  if (!res.ok) {
    let msg: string | null = null;
    if (body && typeof body === "object" && typeof (body as { detail?: unknown }).detail === "string") {
      msg = (body as { detail: string }).detail.trim() || null;
    }
    throw new Error(msg ?? `metrics failed: ${res.status}`);
  }
  const b = body && typeof body === "object" ? body : {};
  return {
    n: typeof b.n === "number" ? b.n : 0,
    by_rating:
      b.by_rating && typeof b.by_rating === "object"
        ? (b.by_rating as { again: number; hard: number; good: number; easy: number })
        : { again: 0, hard: 0, good: 0, easy: 0 },
    again_rate: typeof b.again_rate === "number" ? b.again_rate : 0,
    retention_proxy: typeof b.retention_proxy === "number" ? b.retention_proxy : 0,
    avg_time_ms: typeof b.avg_time_ms === "number" ? b.avg_time_ms : 0,
    daily_goal_reviews: typeof b.daily_goal_reviews === "number" ? b.daily_goal_reviews : b.daily_goal_reviews === null ? null : undefined,
    reviews_done_today: typeof b.reviews_done_today === "number" ? b.reviews_done_today : undefined,
    streak_days: typeof b.streak_days === "number" ? b.streak_days : undefined,
  } as MetricsResponse;
}
