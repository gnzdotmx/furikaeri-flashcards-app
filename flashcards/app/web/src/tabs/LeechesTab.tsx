import React, { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { fetchDeckLeeches, setCardSuspended } from "../api";
import { LEECH_LAPSES_THRESHOLD } from "../constants";
import { leechCardSummary } from "../utils";
import type { Deck } from "../api";
import type { LeechCard } from "../api";
import type { DeckLeechesResponse } from "../api";

export type LeechesTabProps = {
  onGoToSearch: (query: string) => void;
};

export function LeechesTab({ onGoToSearch }: LeechesTabProps) {
  const { decks, selectedDeckId, setError, busy } = useApp();
  const [leechesDeckId, setLeechesDeckId] = useState<string>("");
  const [leechesData, setLeechesData] = useState<DeckLeechesResponse | null>(null);
  const [leechesLoading, setLeechesLoading] = useState(false);
  const [leechesError, setLeechesError] = useState<string | null>(null);

  useEffect(() => {
    if (decks && decks.length > 0 && !leechesDeckId) setLeechesDeckId(selectedDeckId || decks[0].id);
  }, [decks, leechesDeckId, selectedDeckId]);

  useEffect(() => {
    if (!leechesDeckId) return;
    setLeechesError(null);
    setLeechesLoading(true);
    fetchDeckLeeches(leechesDeckId)
      .then((data) => {
        setLeechesData(data);
        setLeechesError(null);
      })
      .catch((e: unknown) => {
        setLeechesError(e instanceof Error ? e.message : "Failed to load leeches");
        setLeechesData(null);
      })
      .finally(() => setLeechesLoading(false));
  }, [leechesDeckId]);

  const handleRefresh = () => {
    if (!leechesDeckId) return;
    setLeechesLoading(true);
    setLeechesError(null);
    fetchDeckLeeches(leechesDeckId)
      .then((data) => {
        setLeechesData(data);
        setLeechesError(null);
      })
      .catch((e: unknown) => {
        setLeechesError(e instanceof Error ? e.message : "Failed to load");
        setLeechesData(null);
      })
      .finally(() => setLeechesLoading(false));
  };

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Leeches</div>
          <div className="panelSubtitle">Cards that lapse often (≥{LEECH_LAPSES_THRESHOLD} lapses). Suspend to exclude from sessions, or fix them (simplify, add context, split).</div>
        </div>
      </div>

      {decks && decks.length > 0 ? (
        <>
          <div className="row" style={{ marginBottom: "1rem" }}>
            <label className="label">
              Deck
              <select className="input" value={leechesDeckId} onChange={(e) => setLeechesDeckId(e.target.value)} disabled={leechesLoading}>
                {decks.map((d: Deck) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </label>
            <button type="button" className="button buttonSecondary" onClick={handleRefresh} disabled={!leechesDeckId || leechesLoading}>
              Refresh
            </button>
          </div>

          {leechesError ? <div className="alert" role="alert">{leechesError}</div> : null}
          {leechesLoading && !leechesData ? <p className="muted">Loading leeches…</p> : null}

          {leechesData && !leechesLoading ? (
            leechesData.leeches.length === 0 ? (
              <p className="muted">No leeches in this deck. Cards are marked leeches after {LEECH_LAPSES_THRESHOLD}+ lapses.</p>
            ) : (
              <ul className="exampleList" style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {leechesData.leeches.map((card: LeechCard) => {
                  const { summary, searchQuery } = leechCardSummary(card);
                  const suspended = Boolean(card.suspended);
                  return (
                    <li key={card.id} style={{ marginBottom: "1rem", padding: "0.75rem", border: "1px solid var(--border)", borderRadius: 8 }}>
                      <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem", alignItems: "center", marginBottom: 4 }}>
                        <span className="jpText" style={{ flex: "1 1 200px", minWidth: 0 }}>{summary || "(no text)"}</span>
                        <span className="badge" title="Lapse count">Lapses: {card.lapses}</span>
                        {suspended ? <span className="badge" style={{ opacity: 0.9 }}>Suspended</span> : null}
                      </div>
                      <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
                        <button
                          type="button"
                          className="button buttonSecondary"
                          disabled={busy}
                          onClick={async () => {
                            setError(null);
                            try {
                              await setCardSuspended(card.id, !suspended);
                              const data = await fetchDeckLeeches(leechesData.deck_id);
                              setLeechesData(data);
                            } catch (e: unknown) {
                              setError(e instanceof Error ? e.message : "Failed to update");
                            }
                          }}
                        >
                          {suspended ? "Unsuspend" : "Suspend"}
                        </button>
                        <button
                          type="button"
                          className="button buttonSecondary"
                          onClick={() => onGoToSearch(searchQuery)}
                        >
                          Search
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )
          ) : null}
        </>
      ) : (
        <p className="muted">No decks. Import content first.</p>
      )}
    </section>
  );
}
