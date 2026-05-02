import { authHeaders } from "./core";

/** Safe filename for a downloaded CSV (no path separators). */
function safeCsvFilename(name: string): string {
  const base = name.replace(/[/\\?%*:|"<>]/g, "_").trim() || "deck";
  return /\.csv$/i.test(base) ? base : `${base}.csv`;
}

function parseFilenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const star = /filename\*=(?:UTF-8'')?([^;\n]+)/i.exec(header);
  if (star) {
    const raw = star[1].trim().replace(/^"|"$/g, "");
    try {
      return decodeURIComponent(raw);
    } catch {
      return raw;
    }
  }
  const quoted = /filename="([^"]+)"/i.exec(header);
  if (quoted) return quoted[1].trim();
  const plain = /filename=([^;\s]+)/i.exec(header);
  return plain ? plain[1].trim().replace(/^"|"$/g, "") : null;
}

/**
 * Download deck CSV in the same header-based format as import (grammar / kanji / vocabulary).
 * Uses Bearer auth so export works when the session is token-only (not cookie-only).
 */
export async function downloadDeckImportFormatCsv(deckId: string, deckDisplayName?: string): Promise<void> {
  const res = await fetch(`/api/exports/decks/${encodeURIComponent(deckId)}/cards.csv`, {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!res.ok) {
    let msg = `export failed: ${res.status}`;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      try {
        const body = (await res.json()) as { detail?: string };
        if (body.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      } catch {
        // ignore
      }
    }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    const fromHeader = parseFilenameFromContentDisposition(res.headers.get("Content-Disposition"));
    a.download =
      (fromHeader && safeCsvFilename(fromHeader)) ||
      (deckDisplayName ? safeCsvFilename(deckDisplayName) : `deck_${deckId.slice(0, 8)}.csv`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
