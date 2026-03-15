import React, { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { downloadDeckCardsCsv } from "../api";
import type { Deck } from "../api";
import type { DeckCardsResponse } from "../api";

export function DecksTab() {
  const { decks, selectedDeckId, setSelectedDeckId, onLoadDeckCards, busy } = useApp();
  const [deckCards, setDeckCards] = useState<DeckCardsResponse | null>(null);

  useEffect(() => {
    if (!selectedDeckId) {
      setDeckCards(null);
      return;
    }
    let cancelled = false;
    onLoadDeckCards(selectedDeckId)
      .then((data) => {
        if (!cancelled) setDeckCards(data);
      })
      .catch(() => {
        // error already set by onLoadDeckCards in AppContext
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDeckId, onLoadDeckCards]);

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Decks</div>
          <div className="panelSubtitle">Manage decks and exports</div>
        </div>
      </div>

      {decks && decks.length > 0 ? (
        <>
          <div className="row">
            <label className="label">
              Deck
              <select
                className="input"
                value={selectedDeckId}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedDeckId(e.target.value)}
              >
                {!decks || decks.length === 0 ? (
                  <option value="">— Refresh to load decks —</option>
                ) : null}
                {decks.map((d: Deck) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <button className="button buttonSecondary" onClick={() => downloadDeckCardsCsv(selectedDeckId)} disabled={!selectedDeckId || busy}>
              Export cards CSV
            </button>
          </div>

          {deckCards ? (
            <>
              <div className="panelSubTitle">Cards by type</div>
              <div className="chips">
                {Object.entries(deckCards.counts_by_type).map(([k, v]) => (
                  <span key={k} className="chip">
                    {k}: {v}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <div className="muted">Select a deck to view its card summary.</div>
          )}
        </>
      ) : (
        <div className="muted">No decks yet. Import a CSV first.</div>
      )}
    </section>
  );
}
