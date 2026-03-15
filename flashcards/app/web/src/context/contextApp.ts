import React from "react";
import type { Deck } from "../api";
import type { DeckCardsResponse } from "../api";
import type { HealthResponse } from "../api";

export type TabId = "study" | "import" | "decks" | "examples" | "metrics" | "leeches" | "account" | "debug";

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

export const AppContext = React.createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = React.useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
