import React, { useCallback, useState } from "react";
import { deleteDeck, downloadDeckImportFormatCsv } from "../api";
import { useApp } from "../context/AppContext";
import { deckLevel, deckSourceType } from "../utils";
import type { ImportResult, SyncImportResult, SyncMergeExisting, SyncSourceType } from "../api";

export type ImportTabProps = {
  level: string;
  setLevel: (l: string) => void;
  importResult: ImportResult | null;
  setImportResult: (r: ImportResult | null) => void;
  syncResult: SyncImportResult | null;
  setSyncResult: (r: SyncImportResult | null) => void;
  syncDeckId: string;
  setSyncDeckId: (id: string) => void;
  syncLevel: string;
  setSyncLevel: (l: string) => void;
  syncSourceType: SyncSourceType;
  setSyncSourceType: (t: SyncSourceType) => void;
  syncFormat: string;
  setSyncFormat: (f: string) => void;
  syncMergeExisting: SyncMergeExisting;
  setSyncMergeExisting: (m: SyncMergeExisting) => void;
  deckName: string;
  setDeckName: (name: string) => void;
  onImportGrammar: (ev: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onImportGenericVocab: (ev: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onImportKanji: (ev: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onSyncImport: (ev: React.FormEvent<HTMLFormElement>) => Promise<void>;
};

export function ImportTab(props: ImportTabProps) {
  const {
    level,
    setLevel,
    importResult,
    syncResult,
    syncDeckId,
    setSyncDeckId,
    syncLevel,
    setSyncLevel,
    syncSourceType,
    setSyncSourceType,
    syncFormat,
    setSyncFormat,
    syncMergeExisting,
    setSyncMergeExisting,
    deckName,
    setDeckName,
    onImportGrammar,
    onImportGenericVocab,
    onImportKanji,
    onSyncImport,
  } = props;
  const { decks, busy, setError, onRefreshDecks, selectedDeckId, setSelectedDeckId } = useApp();
  const [exportDeckId, setExportDeckId] = useState<string>("");
  const [exportBusy, setExportBusy] = useState(false);
  const [deleteDeckId, setDeleteDeckId] = useState<string>("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [activeImportSource, setActiveImportSource] = useState<"grammar" | "vocabulary" | "kanji">("grammar");

  const onExportCsv = useCallback(async () => {
    if (!exportDeckId) return;
    setError(null);
    setExportBusy(true);
    try {
      const deck = (decks ?? []).find((d) => d.id === exportDeckId);
      await downloadDeckImportFormatCsv(exportDeckId, deck?.name);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExportBusy(false);
    }
  }, [decks, exportDeckId, setError]);

  const onDeleteDeck = useCallback(async () => {
    if (!deleteDeckId) return;
    setError(null);
    setDeleteBusy(true);
    try {
      await deleteDeck(deleteDeckId);
      if (selectedDeckId === deleteDeckId) setSelectedDeckId("");
      await onRefreshDecks();
      setDeleteDeckId("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleteBusy(false);
    }
  }, [deleteDeckId, onRefreshDecks, selectedDeckId, setError, setSelectedDeckId]);

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Decks</div>
          <div className="panelSubtitle">
            Import grammar, vocabulary, and kanji from CSV, or export a deck in the same header-based format for editing and re-import.
          </div>
        </div>
      </div>

      <div className="panelSubcard importSection">
        <div className="panelSubTitle" style={{ marginTop: 0 }}>
          Import from CSV
        </div>

        <div className="row">
          <label className="label">
            Level
            <select className="input" value={level} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLevel(e.target.value)}>
              {["N5", "N4", "N3", "N2", "N1", "custom"].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
          {level === "custom" ? (
            <label className="label">
              Deck name (optional)
              <input
                className="input"
                type="text"
                value={deckName}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDeckName(e.target.value)}
                placeholder="e.g. My vocab deck"
                disabled={busy}
                aria-label="Deck name (optional)"
              />
            </label>
          ) : null}
          <span className="muted">{busy ? "Working…" : ""}</span>
        </div>

        <div className="importTabs" role="tablist" aria-label="Import source type">
          <button
            type="button"
            role="tab"
            id="import-tab-grammar"
            aria-selected={activeImportSource === "grammar"}
            aria-controls="import-panel-grammar"
            onClick={() => setActiveImportSource("grammar")}
            disabled={busy}
          >
            Grammar
          </button>
          <button
            type="button"
            role="tab"
            id="import-tab-vocabulary"
            aria-selected={activeImportSource === "vocabulary"}
            aria-controls="import-panel-vocabulary"
            onClick={() => setActiveImportSource("vocabulary")}
            disabled={busy}
          >
            Vocabulary
          </button>
          <button
            type="button"
            role="tab"
            id="import-tab-kanji"
            aria-selected={activeImportSource === "kanji"}
            aria-controls="import-panel-kanji"
            onClick={() => setActiveImportSource("kanji")}
            disabled={busy}
          >
            Kanji
          </button>
        </div>

        {activeImportSource === "grammar" ? (
          <div id="import-panel-grammar" role="tabpanel" aria-labelledby="import-tab-grammar" className="panelSubcard importStackItem">
            <div className="panelSubTitle">Grammar</div>
            <p className="muted" style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.85rem" }}>
              CSV header:{" "}
              <code>japanese_expression, english_meaning, grammar_structure, labels, notes, example_1, example_2, …</code>
            </p>
            <form onSubmit={onImportGrammar} className="importRow">
              <input className="input" type="file" name="grammarFile" accept=".csv,text/csv" disabled={busy} aria-label="Choose grammar CSV" />
              <button className="button buttonPrimary" type="submit" disabled={busy}>Import</button>
            </form>
          </div>
        ) : null}

        {activeImportSource === "vocabulary" ? (
          <div id="import-panel-vocabulary" role="tabpanel" aria-labelledby="import-tab-vocabulary" className="panelSubcard importStackItem">
            <div className="panelSubTitle">Vocabulary</div>
            <p className="muted" style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.85rem" }}>
              CSV header:{" "}
              <code>rank, word, reading_kana, reading_romaji, part_of_speech, labels, notes, meaning, example_1, example_2, …</code>
            </p>
            <form onSubmit={onImportGenericVocab} className="importRow">
              <input className="input" type="file" name="vocabFile" accept=".csv,text/csv" disabled={busy} aria-label="Choose vocabulary CSV" />
              <button className="button buttonPrimary" type="submit" disabled={busy}>Import</button>
            </form>
          </div>
        ) : null}

        {activeImportSource === "kanji" ? (
          <div id="import-panel-kanji" role="tabpanel" aria-labelledby="import-tab-kanji" className="panelSubcard importStackItem">
            <div className="panelSubTitle">Kanji</div>
            <p className="muted" style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.85rem" }}>
              CSV header:{" "}
              <code>rank, kanji, onyomi, kunyomi, meaning, labels, notes, example_1, example_2, …</code>
            </p>
            <form onSubmit={onImportKanji} className="importRow">
              <input className="input" type="file" name="kanjiFile" accept=".csv,text/csv" disabled={busy} aria-label="Choose kanji CSV" />
              <button className="button buttonPrimary" type="submit" disabled={busy}>Import</button>
            </form>
          </div>
        ) : null}
      </div>

      <div className="panelSubcard exportSection importExportSection" style={{ marginTop: "1rem" }}>
        <div className="panelSubTitle" id="export-heading">
          Export to CSV
        </div>
        <p className="muted" style={{ marginBottom: "0.75rem", fontSize: "0.9rem" }}>
          Download uses the same CSV columns as import.
        </p>
        <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: "0.75rem" }}>
          <label className="label" style={{ flex: "1 1 12rem", minWidth: 0 }}>
            Deck to export
            <select
              className="input"
              value={exportDeckId}
              onChange={(e) => setExportDeckId(e.target.value)}
              disabled={busy || exportBusy}
            >
              <option value="">— Select deck —</option>
              {(decks ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button buttonSecondary"
            onClick={() => void onExportCsv()}
            disabled={!exportDeckId || busy || exportBusy}
            aria-label="Export selected deck as CSV"
          >
            {exportBusy ? "Exporting…" : "Export"}
          </button>
        </div>
      </div>

      <div className="panelSubcard syncSection" style={{ marginTop: "1rem" }}>
        <div className="panelSubTitle">Delete deck</div>
        <div className="row" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: "0.75rem" }}>
          <label className="label" style={{ flex: "1 1 12rem", minWidth: 0 }}>
            Deck to delete
            <select
              className="input"
              value={deleteDeckId}
              onChange={(e) => setDeleteDeckId(e.target.value)}
              disabled={busy || deleteBusy}
              aria-label="Deck to delete"
            >
              <option value="">— Select deck —</option>
              {(decks ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button buttonSecondary"
            onClick={() => void onDeleteDeck()}
            disabled={!deleteDeckId || busy || deleteBusy}
            aria-label="Delete selected deck"
          >
            {deleteBusy ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>

      <div className="panelSubcard syncSection" style={{ marginTop: "1rem" }}>
        <div className="panelSubTitle">Reimport / Sync</div>
        <p className="muted" style={{ marginBottom: "0.75rem", fontSize: "0.9rem" }}>
          Upload the same CSV format to an existing deck. Existing notes can be skipped, merged by examples, or fully replaced from CSV fields.
        </p>
        <form onSubmit={onSyncImport}>
          <label className="row" style={{ alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span className="muted" style={{ minWidth: 80 }}>Deck:</span>
            <select
              className="input"
              value={syncDeckId}
              onChange={(e) => {
                const id = e.target.value;
                setSyncDeckId(id);
                const deck = (decks ?? []).find((d) => d.id === id);
                if (deck) {
                  const levelFromDeck = deckLevel(deck);
                  if (levelFromDeck) setSyncLevel(levelFromDeck);
                  const typeFromDeck = deckSourceType(deck);
                  setSyncSourceType(typeFromDeck);
                  setSyncFormat("default");
                }
              }}
              disabled={busy}
              style={{ flex: 1, minWidth: 0 }}
            >
              <option value="">— Select deck —</option>
              {(decks ?? []).map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </label>
          <label className="row" style={{ alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span className="muted" style={{ minWidth: 80 }}>Level:</span>
            <select className="input" value={syncLevel} onChange={(e) => setSyncLevel(e.target.value)} disabled={busy || !!syncDeckId} style={{ width: 80 }}>
              {["N5", "N4", "N3", "N2", "N1", "custom"].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
          <label className="row" style={{ alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span className="muted" style={{ minWidth: 80 }}>Format:</span>
            <select className="input" value={syncFormat} onChange={(e) => setSyncFormat(e.target.value)} disabled={busy || !!syncDeckId} style={{ minWidth: 220 }}>
              {syncSourceType === "grammar" && (
                <option value="default">Grammar (header-based CSV)</option>
              )}
              {syncSourceType === "kanji" && (
                <option value="default">Kanji (header-based CSV)</option>
              )}
              {syncSourceType === "vocabulary" && (
                <option value="default">Vocabulary (header-based CSV)</option>
              )}
            </select>
          </label>
          <label className="row" style={{ alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span className="muted" style={{ minWidth: 80 }}>Existing:</span>
            <select className="input" value={syncMergeExisting} onChange={(e) => setSyncMergeExisting(e.target.value as SyncMergeExisting)} disabled={busy} style={{ minWidth: 180 }}>
              <option value="skip">Skip (only add new)</option>
              <option value="merge_examples">Merge examples into existing</option>
              <option value="replace_existing">Replace existing from CSV (fields)</option>
            </select>
          </label>
          <div className="row" style={{ marginTop: 8 }}>
            <input className="input" type="file" name="syncFile" accept=".csv,text/csv" disabled={busy} />
            <button className="button buttonPrimary" type="submit" disabled={busy}>Sync</button>
          </div>
        </form>
      </div>

      {syncResult ? (
        <div className="statGrid" aria-label="Last sync result" style={{ marginTop: "1rem" }}>
          <div className="stat"><div className="statLabel">Deck</div><div className="statValue">{syncResult.deck_name}</div></div>
          <div className="stat"><div className="statLabel">New notes</div><div className="statValue">{syncResult.created_notes}</div></div>
          <div className="stat"><div className="statLabel">Updated</div><div className="statValue">{syncResult.updated_notes}</div></div>
          <div className="stat"><div className="statLabel">Skipped (existing)</div><div className="statValue">{syncResult.skipped ?? 0}</div></div>
          <div className="stat"><div className="statLabel">Cards generated</div><div className="statValue">{syncResult.created_cards}</div></div>
        </div>
      ) : null}

      {importResult ? (
        <div className="statGrid" aria-label="Last import result">
          <div className="stat"><div className="statLabel">Deck</div><div className="statValue">{importResult.deck_name}</div></div>
          <div className="stat"><div className="statLabel">Notes created</div><div className="statValue">{importResult.created_notes}</div></div>
          <div className="stat"><div className="statLabel">Notes updated</div><div className="statValue">{importResult.updated_notes}</div></div>
          <div className="stat"><div className="statLabel">Cards generated</div><div className="statValue">{importResult.created_cards}</div></div>
        </div>
      ) : null}
    </section>
  );
}
