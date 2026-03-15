import React from "react";
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
  const { decks, busy } = useApp();

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Import</div>
          <div className="panelSubtitle">Bring in CSVs for grammar, vocabulary, and kanji</div>
        </div>
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
        <span className="muted">{busy ? "Working…" : ""}</span>
      </div>

      <div className="importStack" role="list" aria-label="Import options">
        <div className="panelSubcard importStackItem" role="listitem">
          <div className="panelSubTitle">Grammar</div>
          <p className="muted" style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.85rem" }}>
            CSV header: <code>japanese_expression, english_meaning, grammar_structure, example_1, example_2, …</code>
          </p>
          <form onSubmit={onImportGrammar} className="importRow">
            <input className="input" type="file" name="grammarFile" accept=".csv,text/csv" disabled={busy} aria-label="Choose grammar CSV" />
            <button className="button buttonPrimary" type="submit" disabled={busy}>Import</button>
          </form>
        </div>

        <div className="panelSubcard importStackItem" role="listitem">
          <div className="panelSubTitle">Vocabulary</div>
          <p className="muted" style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.85rem" }}>
            CSV header: <code>rank, word, reading_kana, reading_romaji, part_of_speech, meaning, example_1, example_2, …</code>
          </p>
          <form onSubmit={onImportGenericVocab} className="importRow">
            <input className="input" type="file" name="vocabFile" accept=".csv,text/csv" disabled={busy} aria-label="Choose vocabulary CSV" />
            <button className="button buttonPrimary" type="submit" disabled={busy}>Import</button>
          </form>
        </div>

        <div className="panelSubcard importStackItem" role="listitem">
          <div className="panelSubTitle">Kanji</div>
          <p className="muted" style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.85rem" }}>
            CSV header: <code>rank, kanji, onyomi, kunyomi, meaning, example_1, example_2, …</code>
          </p>
          <form onSubmit={onImportKanji} className="importRow">
            <input className="input" type="file" name="kanjiFile" accept=".csv,text/csv" disabled={busy} aria-label="Choose kanji CSV" />
            <button className="button buttonPrimary" type="submit" disabled={busy}>Import</button>
          </form>
        </div>
      </div>

      <div className="panelSubcard" style={{ marginTop: "1rem" }}>
        <div className="panelSubTitle">Reimport / Sync</div>
        <p className="muted" style={{ marginBottom: "0.75rem", fontSize: "0.9rem" }}>
          Upload the same CSV format to an existing deck. Only new rows are added; existing notes are skipped or merged (examples).
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
            <select className="input" value={syncLevel} onChange={(e) => setSyncLevel(e.target.value)} disabled={busy} style={{ width: 80 }}>
              {["N5", "N4", "N3", "N2", "N1", "custom"].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
          <label className="row" style={{ alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span className="muted" style={{ minWidth: 80 }}>Format:</span>
            <select className="input" value={syncFormat} onChange={(e) => setSyncFormat(e.target.value)} disabled={busy} style={{ minWidth: 220 }}>
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
