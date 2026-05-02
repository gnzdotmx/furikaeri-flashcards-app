import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ImportTab, type ImportTabProps } from "./ImportTab";
import { AppContext } from "../context/AppContext";
import type { AppContextValue } from "../context/AppContext";
import * as api from "../api";

const downloadDeckImportFormatCsv = vi.spyOn(api, "downloadDeckImportFormatCsv");
const deleteDeck = vi.spyOn(api, "deleteDeck");

function buildProps(overrides: Partial<ImportTabProps> = {}): ImportTabProps {
  const prevent = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    return Promise.resolve();
  };
  return {
    level: "N5",
    setLevel: vi.fn(),
    importResult: null,
    setImportResult: vi.fn(),
    syncResult: null,
    setSyncResult: vi.fn(),
    syncDeckId: "",
    setSyncDeckId: vi.fn(),
    syncLevel: "N5",
    setSyncLevel: vi.fn(),
    syncSourceType: "grammar",
    setSyncSourceType: vi.fn(),
    syncFormat: "default",
    setSyncFormat: vi.fn(),
    syncMergeExisting: "skip",
    setSyncMergeExisting: vi.fn(),
    deckName: "",
    setDeckName: vi.fn(),
    onImportGrammar: prevent,
    onImportGenericVocab: prevent,
    onImportKanji: prevent,
    onSyncImport: prevent,
    ...overrides,
  };
}

const baseApp: AppContextValue = {
  tab: "import",
  setTab: vi.fn(),
  decks: [{ id: "d1", name: "Deck One", description: null }],
  setDecks: vi.fn(),
  selectedDeckId: "d1",
  setSelectedDeckId: vi.fn(),
  error: null,
  setError: vi.fn(),
  busy: false,
  setBusy: vi.fn(),
  health: null,
  setHealth: vi.fn(),
  onRefreshDecks: vi.fn().mockResolvedValue(undefined),
  onLoadDeckCards: vi.fn().mockResolvedValue({ counts_by_type: {} }),
};

function renderImportTab(props?: Partial<ImportTabProps>, app?: Partial<AppContextValue>) {
  const ctx: AppContextValue = { ...baseApp, ...app };
  return render(
    <AppContext.Provider value={ctx}>
      <ImportTab {...buildProps(props)} />
    </AppContext.Provider>
  );
}

describe("ImportTab", () => {
  beforeEach(() => {
    downloadDeckImportFormatCsv.mockResolvedValue(undefined);
    deleteDeck.mockResolvedValue({ deck_id: "d1", deleted: true });
  });

  afterEach(() => {
    downloadDeckImportFormatCsv.mockReset();
    deleteDeck.mockReset();
  });

  it("shows Decks heading and separate Import and Export sections", () => {
    renderImportTab();
    expect(screen.getByText("Decks")).toBeInTheDocument();
    expect(screen.getByText("Import from CSV")).toBeInTheDocument();
    expect(screen.getByText("Export to CSV")).toBeInTheDocument();
  });

  it("defaults to the Grammar import panel", () => {
    renderImportTab();
    expect(screen.getByLabelText(/choose grammar csv/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/choose vocabulary csv/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/choose kanji csv/i)).not.toBeInTheDocument();
  });

  it("switches import source tabs to show Vocabulary panel", () => {
    renderImportTab();
    fireEvent.click(screen.getByRole("tab", { name: /vocabulary/i }));
    expect(screen.getByLabelText(/choose vocabulary csv/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/choose grammar csv/i)).not.toBeInTheDocument();
  });

  it("disables Export until a deck is selected", () => {
    renderImportTab();
    const exportBtn = screen.getByRole("button", { name: /export selected deck as csv/i });
    expect(exportBtn).toBeDisabled();
    const deckSelect = screen.getByRole("combobox", { name: /deck to export/i });
    fireEvent.change(deckSelect, { target: { value: "d1" } });
    expect(exportBtn).not.toBeDisabled();
  });

  it("calls downloadDeckImportFormatCsv when Export is clicked", async () => {
    renderImportTab();
    fireEvent.change(screen.getByRole("combobox", { name: /deck to export/i }), { target: { value: "d1" } });
    fireEvent.click(screen.getByRole("button", { name: /export selected deck as csv/i }));
    await waitFor(() => {
      expect(downloadDeckImportFormatCsv).toHaveBeenCalledWith("d1", "Deck One");
    });
  });

  it("disables Export when app busy", () => {
    renderImportTab(undefined, { busy: true });
    fireEvent.change(screen.getByRole("combobox", { name: /deck to export/i }), { target: { value: "d1" } });
    expect(screen.getByRole("button", { name: /export selected deck as csv/i })).toBeDisabled();
  });

  it("disables Delete until a deck is selected", () => {
    renderImportTab();
    const deleteBtn = screen.getByRole("button", { name: /delete selected deck/i });
    expect(deleteBtn).toBeDisabled();
    fireEvent.change(screen.getByRole("combobox", { name: /deck to delete/i }), { target: { value: "d1" } });
    expect(deleteBtn).not.toBeDisabled();
  });

  it("calls deleteDeck when Delete is clicked", async () => {
    renderImportTab();
    fireEvent.change(screen.getByRole("combobox", { name: /deck to delete/i }), { target: { value: "d1" } });
    fireEvent.click(screen.getByRole("button", { name: /delete selected deck/i }));
    await waitFor(() => {
      expect(deleteDeck).toHaveBeenCalledWith("d1");
    });
  });

  it("shows replace_existing sync option", () => {
    renderImportTab();
    expect(screen.getByRole("option", { name: /replace existing from csv/i })).toBeInTheDocument();
  });
});
