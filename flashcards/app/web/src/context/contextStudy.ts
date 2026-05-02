import React from "react";
import type { Deck } from "../api";
import type { NextCardResponse, SessionCard, SessionStartResponse } from "../api";
import type { FuriganaMode } from "../studyCardUtils";

export type SessionGoalType = "none" | "short_session" | "session_goal";

export function getCurrentCard(r: NextCardResponse | null): SessionCard | undefined {
  return r && r.kind !== "done" ? r.card : undefined;
}

export type StudyContextValue = {
  decks: Deck[] | null;
  studyDecks: Deck[];
  studyLevel: string;
  setStudyLevel: (v: string) => void;
  selectedDeckId: string;
  setSelectedDeckId: (v: string) => void;
  session: SessionStartResponse | null;
  current: NextCardResponse | null;
  revealed: boolean;
  setRevealed: (v: boolean | ((prev: boolean) => boolean)) => void;
  furiganaMode: FuriganaMode;
  setFuriganaMode: (v: FuriganaMode) => void;
  busy: boolean;
  hintsUsed: number;
  answerSavedFlash: boolean;
  answerSavedTotal: number | null;
  audioError: string | null;
  autoPlayListening: boolean;
  setAutoPlayListening: (v: boolean) => void;
  sessionGoalType: SessionGoalType;
  setSessionGoalType: (v: SessionGoalType) => void;
  sessionGoalShortCards: number;
  setSessionGoalShortCards: (v: number) => void;
  sessionGoalShortMinutes: number;
  setSessionGoalShortMinutes: (v: number) => void;
  sessionGoalReviews: number;
  setSessionGoalReviews: (v: number) => void;
  sessionGoalReached: boolean;
  setSessionGoalReached: (v: boolean) => void;
  sessionReviewsDone: number;
  userSettings: { daily_goal_reviews: number | null } | null;
  onSaveDailyGoal: (value: number | null) => Promise<void>;
  onLoadDeckCards: (deckId: string) => Promise<void>;
  onStartSession: () => Promise<void>;
  onEndSession: () => void;
  onRate: (rating: "again" | "hard" | "good" | "easy") => void;
  onPlayAudio: () => void;
  onFuriganaChange: (mode: FuriganaMode) => void;
  onRevealToggle: () => void;
  onRefreshDecks: () => Promise<void>;
  setTab: (tab: "study" | "import" | "examples" | "metrics" | "debug") => void;
  catchUpMode: boolean;
  setCatchUpMode: (v: boolean) => void;
  includeListening: boolean;
  setIncludeListening: (v: boolean) => void;
  studyFromExamples: boolean;
  setStudyFromExamples: (v: boolean) => void;
};

export const StudyContext = React.createContext<StudyContextValue | null>(null);

export function useStudy(): StudyContextValue {
  const ctx = React.useContext(StudyContext);
  if (!ctx) throw new Error("useStudy must be used within StudyProvider");
  return ctx;
}

export type StudyProviderProps = {
  children: React.ReactNode;
  decks: Deck[] | null;
  selectedDeckId: string;
  setSelectedDeckId: (v: string) => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
  setError: (err: string | null) => void;
  onRefreshDecks: () => Promise<void>;
  onLoadDeckCards: (deckId: string) => Promise<unknown>;
  userSettings: { daily_goal_reviews: number | null } | null;
  setUserSettings: React.Dispatch<React.SetStateAction<{ daily_goal_reviews: number | null } | null>>;
  setTab: (tab: "study" | "import" | "examples" | "metrics" | "debug") => void;
};
