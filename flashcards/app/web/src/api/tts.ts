import { authHeaders } from "./core";

export async function fetchTtsKana(text: string): Promise<string> {
  const res = await fetch(
    `/api/tts/to-kana?${new URLSearchParams({ text, lang: "ja-JP" })}`,
    { headers: authHeaders() }
  );
  const raw = await res.text();
  let body: { kana?: string } | null = null;
  try {
    body = raw ? (JSON.parse(raw) as { kana?: string }) : null;
  } catch {
    if (!res.ok) throw new Error(res.statusText || "Failed to get kana");
  }
  if (!res.ok) throw new Error("Failed to get kana");
  return body?.kana ?? text;
}

export async function tts(text: string, rate: number): Promise<{ url: string }> {
  const res = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ text, lang: "ja-JP", rate }),
  });
  const raw = await res.text();
  let body: { detail?: string; url?: string } | null = null;
  try {
    body = raw ? (JSON.parse(raw) as { detail?: string; url?: string }) : null;
  } catch {
    if (!res.ok) throw new Error(res.statusText ?? raw.slice(0, 80) ?? "TTS failed");
  }
  if (!res.ok) throw new Error(body?.detail ?? res.statusText ?? "TTS failed");
  if (body?.url) return { url: body.url };
  throw new Error("TTS returned no URL");
}
