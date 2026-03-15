import { authHeaders } from "./core";

export type ImportResult = {
  ok: boolean;
  deck_id: string;
  deck_name: string;
  level: string;
  source_type: string;
  created_notes: number;
  updated_notes: number;
  created_cards: number;
  deleted_placeholders?: number;
};

export type SyncImportResult = ImportResult & { skipped: number };

export type SyncSourceType = "grammar" | "kanji" | "vocabulary";

export type SyncMergeExisting = "skip" | "merge_examples";

export async function syncImport(
  deckId: string,
  level: string,
  sourceType: SyncSourceType,
  format: string,
  file: File,
  mergeExisting: SyncMergeExisting = "skip",
  hasHeader: boolean = true,
): Promise<SyncImportResult> {
  const fd = new FormData();
  fd.append("deck_id", deckId);
  fd.append("level", level);
  fd.append("source_type", sourceType);
  fd.append("format", format);
  fd.append("merge_existing", mergeExisting);
  fd.append("has_header", hasHeader ? "true" : "false");
  fd.append("file", file);
  const res = await fetch("/api/imports/sync", {
    method: "POST",
    body: fd,
    headers: authHeaders(),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `sync import failed: ${res.status}`);
  return body as SyncImportResult;
}

export async function importGrammar(
  file: File,
  level: string,
  deckName?: string,
): Promise<ImportResult> {
  const fd = new FormData();
  fd.append("level", level);
  if (deckName && deckName.trim()) {
    fd.append("deck_name", deckName.trim());
  }
  fd.append("merge_policy", "overwrite");
  fd.append("file", file);
  const res = await fetch("/api/imports/grammar", {
    method: "POST",
    body: fd,
    headers: authHeaders(),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `import failed: ${res.status}`);
  return body as ImportResult;
}

export async function importGenericVocab(file: File, level: string, deckName?: string): Promise<ImportResult> {
  const fd = new FormData();
  fd.append("level", level);
  if (deckName && deckName.trim()) {
    fd.append("deck_name", deckName.trim());
  }
  fd.append("merge_policy", "overwrite");
  fd.append("file", file);
  const res = await fetch("/api/imports/vocabulary", {
    method: "POST",
    body: fd,
    headers: authHeaders(),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `import failed: ${res.status}`);
  return body as ImportResult;
}

export async function importKanji(file: File, level: string, deckName?: string): Promise<ImportResult> {
  const fd = new FormData();
  fd.append("level", level);
  if (deckName && deckName.trim()) {
    fd.append("deck_name", deckName.trim());
  }
  fd.append("merge_policy", "overwrite");
  fd.append("file", file);
  const res = await fetch("/api/imports/kanji", {
    method: "POST",
    body: fd,
    headers: authHeaders(),
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body?.detail ?? `import failed: ${res.status}`);
  return body as ImportResult;
}
