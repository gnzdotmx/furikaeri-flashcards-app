import React, { useCallback, useEffect, useState } from "react";
import { fetchDecks, fetchHealth, fetchDeckCards } from "../api";
import type { Deck } from "../api";
import type { DeckCardsResponse } from "../api";
import type { HealthResponse } from "../api";

export type TabId = "study" | "import" | "examples" | "metrics" | "leeches";

export type AppContextValue = {
  tab: TabId;
  setTab: (tab: TabId) => void;
  decks: Deck[] | null;
  setDecks: (decks: Deck[] | null) => void;
  selectedDeckId: string;
  setSelectedDeckId: (id: string) => void;
  error: string | null;
  setError: (err: string | null) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
  health: HealthResponse | null;
  setHealth: (h: HealthResponse | null) => void;
  onRefreshDecks: () => Promise<void>;
  onLoadDeckCards: (deckId: string) => Promise<DeckCardsResponse>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const AppContext = React.createContext<AppContextValue | null>(null);

// eslint-disable-next-line react-refresh/only-export-components
export function useApp(): AppContextValue {
  const ctx = React.useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [tab, setTab] = useState<TabId>("study");
  const [decks, setDecks] = useState<Deck[] | null>(null);
  const [selectedDeckId, setSelectedDeckId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const onRefreshDecks = useCallback(async () => {
    setError(null);
    try {
      const d = await fetchDecks();
      setDecks(d);
      if (!selectedDeckId && d.length > 0) setSelectedDeckId(d[0].id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }, [selectedDeckId]);

  const onLoadDeckCards = useCallback(async (deckId: string): Promise<DeckCardsResponse> => {
    setError(null);
    try {
      const data = await fetchDeckCards(deckId);
      return data;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      throw e;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((h) => {
        if (!cancelled) setHealth(h);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Unknown error");
      });
    fetchDecks()
      .then((d) => {
        if (cancelled) return;
        setDecks(d);
        if (!selectedDeckId && d.length > 0) setSelectedDeckId(d[0].id);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [selectedDeckId]);

  const value: AppContextValue = {
    tab,
    setTab,
    decks,
    setDecks,
    selectedDeckId,
    setSelectedDeckId,
    error,
    setError,
    busy,
    setBusy,
    health,
    setHealth,
    onRefreshDecks,
    onLoadDeckCards,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
