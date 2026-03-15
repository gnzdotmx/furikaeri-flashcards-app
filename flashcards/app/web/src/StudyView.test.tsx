import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { StudyView } from "./StudyView";
import {
  StudyContext,
  StudyProvider,
  useStudy,
  type StudyContextValue,
  type StudyProviderProps,
} from "./context/StudyContext";

function StudyViewConsumer() {
  useStudy();
  return <span>consumed</span>;
}

const defaultDecks = [{ id: "deck-1", name: "Test Deck", description: null }];

const defaultProviderProps: Omit<StudyProviderProps, "children"> = {
  decks: defaultDecks,
  selectedDeckId: "deck-1",
  setSelectedDeckId: vi.fn(),
  busy: false,
  setBusy: vi.fn(),
  setError: vi.fn(),
  onRefreshDecks: vi.fn().mockResolvedValue(undefined),
  onLoadDeckCards: vi.fn().mockResolvedValue(undefined),
  userSettings: null,
  setUserSettings: vi.fn(),
  setTab: vi.fn(),
};

function renderWithProvider(providerOverrides: Partial<Omit<StudyProviderProps, "children">> = {}) {
  return render(
    <StudyProvider {...defaultProviderProps} {...providerOverrides}>
      <StudyView />
    </StudyProvider>
  );
}

function buildMockContext(overrides: Partial<StudyContextValue> = {}): StudyContextValue {
  return {
    decks: defaultDecks,
    studyDecks: defaultDecks,
    studyLevel: "All",
    setStudyLevel: vi.fn(),
    selectedDeckId: "deck-1",
    setSelectedDeckId: vi.fn(),
    session: null,
    current: null,
    revealed: false,
    setRevealed: vi.fn(),
    furiganaMode: "hover",
    setFuriganaMode: vi.fn(),
    busy: false,
    hintsUsed: 0,
    answerSavedFlash: false,
    answerSavedTotal: null,
    audioError: null,
    autoPlayListening: false,
    setAutoPlayListening: vi.fn(),
    sessionGoalType: "none",
    setSessionGoalType: vi.fn(),
    sessionGoalShortCards: 10,
    setSessionGoalShortCards: vi.fn(),
    sessionGoalShortMinutes: 5,
    setSessionGoalShortMinutes: vi.fn(),
    sessionGoalReviews: 20,
    setSessionGoalReviews: vi.fn(),
    sessionGoalReached: false,
    setSessionGoalReached: vi.fn(),
    sessionReviewsDone: 0,
    userSettings: null,
    onSaveDailyGoal: vi.fn().mockResolvedValue(undefined),
    onLoadDeckCards: vi.fn().mockResolvedValue(undefined),
    onStartSession: vi.fn().mockResolvedValue(undefined),
    onEndSession: vi.fn(),
    onRate: vi.fn(),
    onPlayAudio: vi.fn(),
    onFuriganaChange: vi.fn(),
    onRevealToggle: vi.fn(),
    onRefreshDecks: vi.fn().mockResolvedValue(undefined),
    setTab: vi.fn(),
    catchUpMode: false,
    setCatchUpMode: vi.fn(),
    includeListening: true,
    setIncludeListening: vi.fn(),
    studyFromExamples: false,
    setStudyFromExamples: vi.fn(),
    studyLabel: null,
    setStudyLabel: vi.fn(),
    onStartLabelSession: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("StudyView", () => {
  it("renders Study title and deck selection", async () => {
    renderWithProvider();
    await screen.findByText("Study");
    expect(screen.getByText("Study")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /level/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /deck/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /label/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^start$/i })).toBeInTheDocument();
  });

  it("Listening cards checkbox is unchecked by default", async () => {
    renderWithProvider();
    await screen.findByText("Study");
    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    const listeningCheckbox = screen.getByRole("checkbox", { name: /listening cards/i });
    expect(listeningCheckbox).not.toBeChecked();
  });

  it("shows Loading when decks is null", async () => {
    renderWithProvider({ decks: null });
    await screen.findByText("Study");
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows empty state when no decks", async () => {
    renderWithProvider({ decks: [], selectedDeckId: "" });
    await screen.findByText("Study");
    expect(screen.getByText(/Import a CSV to get started/)).toBeInTheDocument();
    const importBtn = screen.getByRole("button", { name: /^import$/i });
    expect(importBtn).toBeInTheDocument();
    fireEvent.click(importBtn);
    expect(defaultProviderProps.setTab).toHaveBeenCalledWith("import");
  });

  it("calls onStartSession when Start is clicked with deck selected", async () => {
    const onStartSession = vi.fn().mockResolvedValue(undefined);
    const mockValue = buildMockContext({ onStartSession });
    render(
      <StudyContext.Provider value={mockValue}>
        <StudyView />
      </StudyContext.Provider>
    );
    await screen.findByText("Study");
    const startBtn = screen.getByRole("button", { name: /^start$/i });
    expect(startBtn).not.toBeDisabled();
    fireEvent.click(startBtn);
    expect(onStartSession).toHaveBeenCalledTimes(1);
  });

  it("disables Start when no deck selected", async () => {
    renderWithProvider({ selectedDeckId: "" });
    await screen.findByText("Study");
    const startBtn = screen.getByRole("button", { name: /^start$/i });
    expect(startBtn).toBeDisabled();
  });

  it("shows Starting… and disables Start when busy and no session", async () => {
    renderWithProvider({ busy: true });
    await screen.findByText("Study");
    const startingButtons = screen.getAllByRole("button", { name: /starting/i });
    expect(startingButtons.length).toBeGreaterThanOrEqual(1);
    const startBtn = startingButtons[0];
    expect(startBtn).toHaveTextContent("Starting…");
    expect(startBtn).toBeDisabled();
  });

  it("calls setStudyLevel when Level select changes", async () => {
    const setStudyLevel = vi.fn();
    const mockValue = buildMockContext({ setStudyLevel });
    render(
      <StudyContext.Provider value={mockValue}>
        <StudyView />
      </StudyContext.Provider>
    );
    await screen.findByText("Study");
    const levelSelect = screen.getByRole("combobox", { name: /level/i });
    fireEvent.change(levelSelect, { target: { value: "N5" } });
    expect(setStudyLevel).toHaveBeenCalledWith("N5");
  });

  it("toggles settings panel when Settings button clicked", async () => {
    renderWithProvider();
    await screen.findByText("Study");
    const settingsBtn = screen.getByRole("button", { name: /settings/i });
    expect(settingsBtn).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(settingsBtn);
    expect(screen.getByText("Daily goal")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /hide settings/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /hide settings/i }));
    expect(screen.queryByText("Daily goal")).not.toBeInTheDocument();
  });

  it("shows session progress (due, new, est) when session is active", async () => {
    const session = {
      session_id: "s1",
      deck: { id: "deck-1", name: "Test Deck" },
      due_now: 2,
      due_today: 5,
      new_available: 10,
      new_limit: 5,
      estimated_minutes: 3,
      leech_count: 0,
      daily_goal_reviews: null,
      reviews_done_today: 0,
      streak_days: 0,
    };
    const mockValue = buildMockContext({ session, current: null });
    render(
      <StudyContext.Provider value={mockValue}>
        <StudyView />
      </StudyContext.Provider>
    );
    await screen.findByText("Study");
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText(/~3m/)).toBeInTheDocument();
  });

  it("shows goal reached banner when sessionGoalReached is true", async () => {
    const session = {
      session_id: "s1",
      deck: { id: "deck-1", name: "Test" },
      due_now: 0,
      due_today: 0,
      new_available: 0,
      new_limit: 0,
      estimated_minutes: 0,
      leech_count: 0,
      daily_goal_reviews: null,
      reviews_done_today: 0,
      streak_days: 0,
    };
    const mockValue = buildMockContext({ session, sessionGoalReached: true });
    render(
      <StudyContext.Provider value={mockValue}>
        <StudyView />
      </StudyContext.Provider>
    );
    await screen.findByText("Study");
    const goalReachedBanner = screen.getByText(/goal reached/i).closest("[role=\"status\"]");
    expect(goalReachedBanner).toBeInTheDocument();
  });

  it("has live region for screen reader announcements when session has a card", async () => {
    const session = {
      session_id: "s1",
      deck: { id: "deck-1", name: "Test Deck" },
      due_now: 2,
      new_available: 10,
      new_limit: 5,
      due_today: 5,
      estimated_minutes: 3,
      leech_count: 0,
      daily_goal_reviews: null,
      reviews_done_today: 0,
      streak_days: 0,
    };
    const current = {
      kind: "due" as const,
      new_remaining: 5,
      card: {
        id: "c1",
        note_id: "n1",
        deck_id: "deck-1",
        card_type: "grammar_meaning_recognition",
        created_at: "2020-01-01T00:00:00Z",
        front_template: "{}",
        back_template: "{}",
      },
    };
    const mockValue = buildMockContext({ session, current });
    render(
      <StudyContext.Provider value={mockValue}>
        <StudyView />
      </StudyContext.Provider>
    );
    await screen.findByText("Study");
    const liveRegion = document.getElementById("study-live-region");
    expect(liveRegion).toBeInTheDocument();
    expect(liveRegion).toHaveAttribute("aria-live", "polite");
    expect(liveRegion).toHaveAttribute("role", "status");
    expect(liveRegion?.textContent).toMatch(/Session started/);
    expect(liveRegion?.textContent).toMatch(/Card 1 of 7/);
  });

  it("card region is focusable and has accessible name when session active", async () => {
    const session = {
      session_id: "s1",
      deck: { id: "deck-1", name: "Test Deck" },
      due_now: 1,
      new_available: 5,
      new_limit: 3,
      due_today: 5,
      estimated_minutes: 2,
      leech_count: 0,
      daily_goal_reviews: null,
      reviews_done_today: 0,
      streak_days: 0,
    };
    const current = {
      kind: "due" as const,
      new_remaining: 3,
      card: {
        id: "c1",
        note_id: "n1",
        deck_id: "deck-1",
        card_type: "grammar_meaning_recognition",
        created_at: "2020-01-01T00:00:00Z",
        front_template: "{}",
        back_template: "{}",
      },
    };
    const mockValue = buildMockContext({ session, current });
    render(
      <StudyContext.Provider value={mockValue}>
        <StudyView />
      </StudyContext.Provider>
    );
    await screen.findByText("Study");
    const cardRegion = screen.getByRole("region", { name: /current card/i });
    expect(cardRegion).toHaveAttribute("tabindex", "-1");
  });
});

describe("useStudy", () => {
  it("throws when used outside StudyProvider", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<StudyViewConsumer />)).toThrow(
      "useStudy must be used within StudyProvider"
    );
    consoleSpy.mockRestore();
  });

  it("returns context value when used inside StudyProvider", () => {
    render(
      <StudyProvider {...defaultProviderProps}>
        <StudyViewConsumer />
      </StudyProvider>
    );
    expect(screen.getByText("consumed")).toBeInTheDocument();
  });
});
