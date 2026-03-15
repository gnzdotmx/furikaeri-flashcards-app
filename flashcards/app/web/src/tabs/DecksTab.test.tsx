import { describe, expect, it, vi } from "vitest";
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { DecksTab } from "./DecksTab";
import { AppProvider, AppContext } from "../context/AppContext";
import type { AppContextValue } from "../context/AppContext";

describe("DecksTab", () => {
  it("renders without crashing when wrapped in AppProvider", async () => {
    render(
      <AppProvider>
        <DecksTab />
      </AppProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Decks/)).toBeInTheDocument();
      expect(screen.getByText(/Manage decks and exports/)).toBeInTheDocument();
    });
  });

  it("does not show Load summary button; summary loads when deck is selected", async () => {
    render(
      <AppProvider>
        <DecksTab />
      </AppProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Decks/)).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /load summary/i })).not.toBeInTheDocument();
  });

  it("disables Export cards CSV when busy", async () => {
    const mockValue: AppContextValue = {
      tab: "decks",
      setTab: vi.fn(),
      decks: [{ id: "d1", name: "Deck 1", description: null }],
      setDecks: vi.fn(),
      selectedDeckId: "d1",
      setSelectedDeckId: vi.fn(),
      error: null,
      setError: vi.fn(),
      busy: true,
      setBusy: vi.fn(),
      health: null,
      setHealth: vi.fn(),
      onRefreshDecks: vi.fn().mockResolvedValue(undefined),
      onLoadDeckCards: vi.fn().mockResolvedValue({ counts_by_type: {} }),
    };
    render(
      <AppContext.Provider value={mockValue}>
        <DecksTab />
      </AppContext.Provider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Decks/)).toBeInTheDocument();
    });
    const exportBtn = screen.getByRole("button", { name: /export cards csv/i });
    expect(exportBtn).toBeDisabled();
  });
});
