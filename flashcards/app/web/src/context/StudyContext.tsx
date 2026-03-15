import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  answerCard,
  fetchTtsKana,
  logEvent,
  nextCard,
  startSession,
  updateUserSettings,
  type NextCardResponse,
  type SessionCard,
  type SessionStartResponse,
} from "../api";
import { getTtsTextForCard, type FuriganaMode } from "../StudyCard";
import { deckLevel } from "../utils";
import { safeJson } from "../utils";
import type { Deck } from "../api";

export type SessionGoalType = "none" | "short_session" | "session_goal";

function getCurrentCard(r: NextCardResponse | null): SessionCard | undefined {
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
  setTab: (tab: "study" | "import" | "decks" | "examples" | "metrics") => void;
  catchUpMode: boolean;
  setCatchUpMode: (v: boolean) => void;
  includeListening: boolean;
  setIncludeListening: (v: boolean) => void;
  studyFromExamples: boolean;
  setStudyFromExamples: (v: boolean) => void;
  studyLabel: string | null;
  setStudyLabel: (v: string | null) => void;
  onStartLabelSession: () => Promise<void>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const StudyContext = React.createContext<StudyContextValue | null>(null);

// eslint-disable-next-line react-refresh/only-export-components
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
  setTab: (tab: "study" | "import" | "decks" | "examples" | "metrics") => void;
};

export function StudyProvider({
  children,
  decks,
  selectedDeckId,
  setSelectedDeckId,
  busy,
  setBusy,
  setError,
  onRefreshDecks,
  onLoadDeckCards,
  userSettings,
  setUserSettings,
  setTab,
}: StudyProviderProps) {
  const [studyLevel, setStudyLevel] = useState<string>("All");
  const [session, setSession] = useState<SessionStartResponse | null>(null);
  const [current, setCurrent] = useState<NextCardResponse | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [cardStartMs, setCardStartMs] = useState<number>(0);
  const [furiganaMode, setFuriganaMode] = useState<FuriganaMode>("hover");
  const [hintsUsed, setHintsUsed] = useState(0);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [answerSavedFlash, setAnswerSavedFlash] = useState(false);
  const [answerSavedTotal, setAnswerSavedTotal] = useState<number | null>(null);
  const [sessionReviewsDone, setSessionReviewsDone] = useState(0);
  const [sessionGoalReached, setSessionGoalReached] = useState(false);
  const [catchUpMode, setCatchUpMode] = useState(false);
  const [includeListening, setIncludeListening] = useState(false);
  const [studyFromExamples, setStudyFromExamples] = useState(false);
  const [studyLabel, setStudyLabel] = useState<string | null>(null);
  const [activeLabelFilter, setActiveLabelFilter] = useState<string | null>(null);
  const [autoPlayListening, setAutoPlayListening] = useState(() =>
    typeof localStorage !== "undefined" && localStorage.getItem("vocab_listening_autoplay") === "true"
  );
  const lastTtsRef = useRef<{ cardId: string; text: string; kana: string } | null>(null);
  const sessionStartMsRef = useRef<number>(0);

  const currentCardId = getCurrentCard(current)?.id;

  const [sessionGoalType, setSessionGoalType] = useState<SessionGoalType>(() => {
    if (typeof localStorage === "undefined") return "none";
    const v = localStorage.getItem("session_goal_type") as SessionGoalType | null;
    return v === "short_session" || v === "session_goal" ? v : "none";
  });
  const [sessionGoalShortCards, setSessionGoalShortCards] = useState(() => {
    if (typeof localStorage === "undefined") return 10;
    const n = parseInt(localStorage.getItem("session_goal_short_cards") ?? "10", 10);
    return Number.isFinite(n) && n >= 5 && n <= 30 ? n : 10;
  });
  const [sessionGoalShortMinutes, setSessionGoalShortMinutes] = useState(() => {
    if (typeof localStorage === "undefined") return 5;
    const n = parseInt(localStorage.getItem("session_goal_short_minutes") ?? "5", 10);
    return Number.isFinite(n) && n >= 3 && n <= 20 ? n : 5;
  });
  const [sessionGoalReviews, setSessionGoalReviews] = useState(() => {
    if (typeof localStorage === "undefined") return 20;
    const n = parseInt(localStorage.getItem("session_goal_reviews") ?? "20", 10);
    return Number.isFinite(n) && n >= 5 && n <= 100 ? n : 20;
  });

  const studyDecks = (() => {
    if (!decks) return [];
    if (studyLevel === "All") return decks;
    return decks.filter((d) => deckLevel(d) === studyLevel);
  })();

  useEffect(() => {
    if (!decks) return;
    const filtered = studyLevel === "All" ? decks : decks.filter((d) => deckLevel(d) === studyLevel);
    if (!filtered.length) return;
    if (selectedDeckId && filtered.some((d) => d.id === selectedDeckId)) return;
    setSelectedDeckId(filtered[0].id);
  }, [studyLevel, decks, selectedDeckId, setSelectedDeckId]);

  useEffect(() => {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem("session_goal_type", sessionGoalType);
    localStorage.setItem("session_goal_short_cards", String(sessionGoalShortCards));
    localStorage.setItem("session_goal_short_minutes", String(sessionGoalShortMinutes));
    localStorage.setItem("session_goal_reviews", String(sessionGoalReviews));
  }, [sessionGoalType, sessionGoalShortCards, sessionGoalShortMinutes, sessionGoalReviews]);

  useEffect(() => {
    setRevealed(false);
    setHintsUsed(0);
    setAudioError(null);
    setCardStartMs(Date.now());
    lastTtsRef.current = null;
  }, [currentCardId]);

  const doPlayTtsText = useCallback(
    async (text: string, cardId: string, autoplay = false) => {
      setAudioError(null);
      const cached = lastTtsRef.current;
      const sameCard = cached && cached.cardId === cardId && cached.text === text;
      let kana: string | undefined = sameCard ? cached!.kana : undefined;
      if (!kana) {
        try {
          kana = await fetchTtsKana(text);
        } catch (e: unknown) {
          setAudioError(e instanceof Error ? e.message : "Could not get reading.");
          return;
        }
      }
      lastTtsRef.current = { cardId, text, kana };
      void logEvent("audio_played", {
        session_id: session?.session_id,
        card_id: cardId,
        payload: { tts_text_len: text.length, autoplay },
      });
      try {
        const synth = window.speechSynthesis;
        if (!synth) {
          setAudioError("Browser speech not supported.");
          return;
        }
        synth.cancel();
        const u = new SpeechSynthesisUtterance(kana);
        u.lang = "ja-JP";
        u.rate = 1.0;
        synth.speak(u);
      } catch (e: unknown) {
        setAudioError(e instanceof Error ? e.message : "Playback failed.");
      }
    },
    [session?.session_id]
  );

  useEffect(() => {
    const c = getCurrentCard(current);
    if (!session || !c) return;
    if (c.card_type !== "vocab_listening" || !autoPlayListening) return;
    const front = safeJson<Record<string, unknown>>(c.front_template) ?? {};
    const back = safeJson<Record<string, unknown>>(c.back_template) ?? {};
    const text = getTtsTextForCard(c, front, back);
    if (!text) return;
    const cardId = c.id;
    const t = setTimeout(() => {
      setHintsUsed((n) => n + 1);
      void doPlayTtsText(text, cardId, true);
    }, 300);
    return () => clearTimeout(t);
  }, [currentCardId, current, session, autoPlayListening, doPlayTtsText]);

  useEffect(() => {
    const raw = current && current.kind !== "done" ? current.presentation_defaults?.furigana_mode : undefined;
    if (raw === "off" || raw === "hover" || raw === "on") {
      setFuriganaMode(raw);
    }
  }, [currentCardId, current]);

  const onSaveDailyGoal = useCallback(
    async (value: number | null) => {
      const res = await updateUserSettings({ daily_goal_reviews: value });
      setUserSettings((prev) => (prev ? { ...prev, daily_goal_reviews: res.daily_goal_reviews } : { daily_goal_reviews: res.daily_goal_reviews }));
      setSession((s) => (s ? { ...s, daily_goal_reviews: res.daily_goal_reviews ?? undefined } : null));
    },
    [setUserSettings]
  );

  const onStartSession = useCallback(async () => {
    if (!selectedDeckId) return;
    setError(null);
    setSession(null);
    setCurrent(null);
    setRevealed(false);
    setSessionReviewsDone(0);
    setSessionGoalReached(false);
    setActiveLabelFilter(null);
    setBusy(true);
    try {
      const s = await startSession(selectedDeckId, { catch_up: catchUpMode, include_listening: includeListening });
      setSession(s);
      sessionStartMsRef.current = Date.now();
      const nxt = await nextCard(s.session_id);
      setCurrent(nxt);
      setRevealed(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }, [selectedDeckId, catchUpMode, includeListening, setBusy, setError]);

  const onStartLabelSession = useCallback(async () => {
    if (!selectedDeckId) return;
    const label = studyLabel && studyLabel.trim();
    if (!label) return;
    setError(null);
    setSession(null);
    setCurrent(null);
    setRevealed(false);
    setSessionReviewsDone(0);
    setSessionGoalReached(false);
    setBusy(true);
    try {
      const s = await startSession(selectedDeckId, { catch_up: catchUpMode, include_listening: includeListening });
      setSession(s);
      sessionStartMsRef.current = Date.now();
      setActiveLabelFilter(label);
      const nxt = await nextCard(s.session_id, { label });
      setCurrent(nxt);
      setRevealed(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }, [selectedDeckId, catchUpMode, includeListening, setBusy, setError, studyLabel]);

  const onEndSession = useCallback(() => {
    setSession(null);
    setCurrent(null);
    setRevealed(false);
    setSessionGoalReached(false);
  }, []);

  const onRate = useCallback(
    async (rating: "again" | "hard" | "good" | "easy") => {
      const cardId = getCurrentCard(current)?.id;
      if (!session || !cardId) return;
      setBusy(true);
      setError(null);
      setAnswerSavedFlash(false);
      try {
        const res = await answerCard(session.session_id, cardId, rating, Date.now() - cardStartMs, hintsUsed);
        setAnswerSavedTotal(typeof res.answer_submitted_total === "number" ? res.answer_submitted_total : null);
        setAnswerSavedFlash(true);
        setTimeout(() => setAnswerSavedFlash(false), 2000);
        const nextDone = sessionReviewsDone + 1;
        setSessionReviewsDone(nextDone);
        const elapsedMs = Date.now() - sessionStartMsRef.current;
        const shortTimeReached =
          sessionGoalType === "short_session" &&
          sessionGoalShortMinutes > 0 &&
          elapsedMs >= sessionGoalShortMinutes * 60 * 1000;
        const shortCardsReached = sessionGoalType === "short_session" && nextDone >= sessionGoalShortCards;
        const goalReviewsReached = sessionGoalType === "session_goal" && nextDone >= sessionGoalReviews;
        if (!sessionGoalReached && (shortTimeReached || shortCardsReached || goalReviewsReached)) {
          setSessionGoalReached(true);
        }
        const label = activeLabelFilter && activeLabelFilter.trim() ? activeLabelFilter : null;
        const nxt = await nextCard(session.session_id, label ? { label } : undefined);
        setCurrent(nxt);
        setRevealed(false);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setBusy(false);
      }
    },
    [
      session,
      current,
      cardStartMs,
      hintsUsed,
      sessionReviewsDone,
      sessionGoalType,
      sessionGoalShortMinutes,
      sessionGoalShortCards,
      sessionGoalReviews,
      sessionGoalReached,
      setBusy,
      setError,
      activeLabelFilter,
    ]
  );

  const onPlayAudio = useCallback(() => {
    setAudioError(null);
    setHintsUsed((n) => n + 1);
    const card = getCurrentCard(current);
    if (!session || !card) return;
    const front = safeJson<Record<string, unknown>>(card.front_template) ?? {};
    const back = safeJson<Record<string, unknown>>(card.back_template) ?? {};
    const text = getTtsTextForCard(card, front, back);
    if (!text) {
      setAudioError("No text available to speak for this card.");
      return;
    }
    void doPlayTtsText(text, card.id, false);
  }, [session, current, doPlayTtsText]);

  const onFuriganaChange = useCallback(
    (mode: FuriganaMode) => {
      setFuriganaMode(mode);
      if (mode !== "off") setHintsUsed((n) => n + 1);
      void logEvent("hint_toggled", {
        session_id: session?.session_id,
        card_id: currentCardId,
        payload: { hint: "furigana", mode },
      });
    },
    [session?.session_id, currentCardId]
  );

  const onRevealToggle = useCallback(() => {
    setRevealed((v) => !v);
    void logEvent("reveal_toggled", {
      session_id: session?.session_id,
      card_id: currentCardId,
      payload: {},
    });
  }, [session?.session_id, currentCardId]);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const el = document.activeElement;
      const isTyping = el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA");
      if (isTyping) return;
      if (e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        setRevealed((v) => !v);
        return;
      }
      if (e.key === "1") void onRate("again");
      if (e.key === "2") void onRate("hard");
      if (e.key === "3") void onRate("good");
      if (e.key === "4") void onRate("easy");
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [session, current, cardStartMs, hintsUsed, onRate]);

  const handleLoadDeckCards = useCallback(
    async (deckId: string): Promise<void> => {
      setError(null);
      try {
        await onLoadDeckCards(deckId);
      } catch {
        // error already surfaced via setError if needed
      }
    },
    [onLoadDeckCards, setError]
  );

  const value: StudyContextValue = {
    decks,
    studyDecks,
    studyLevel,
    setStudyLevel,
    selectedDeckId,
    setSelectedDeckId,
    session,
    current,
    revealed,
    setRevealed,
    furiganaMode,
    setFuriganaMode,
    busy,
    hintsUsed,
    answerSavedFlash,
    answerSavedTotal,
    audioError,
    autoPlayListening,
    setAutoPlayListening,
    sessionGoalType,
    setSessionGoalType,
    sessionGoalShortCards,
    setSessionGoalShortCards,
    sessionGoalShortMinutes,
    setSessionGoalShortMinutes,
    sessionGoalReviews,
    setSessionGoalReviews,
    sessionGoalReached,
    setSessionGoalReached,
    sessionReviewsDone,
    userSettings,
    onSaveDailyGoal,
    onLoadDeckCards: handleLoadDeckCards,
    onStartSession,
    onEndSession,
    onRate,
    onPlayAudio,
    onFuriganaChange,
    onRevealToggle,
    onRefreshDecks,
    setTab,
    catchUpMode,
    setCatchUpMode,
    includeListening,
    setIncludeListening,
    studyFromExamples,
    setStudyFromExamples,
    studyLabel,
    setStudyLabel,
    onStartLabelSession,
  };

  return <StudyContext.Provider value={value}>{children}</StudyContext.Provider>;
}
