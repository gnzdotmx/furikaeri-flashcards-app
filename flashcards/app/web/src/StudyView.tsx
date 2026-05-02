import React, { useCallback, useEffect, useRef, useState } from "react";
import type { Deck } from "./api";
import { deleteCardStudyNote, fetchCardStudyNote, fetchDeckLabels, putCardStudyNote } from "./api";
import type { StudyCardCurrent } from "./studyCardUtils";
import { StudyCard } from "./StudyCard";
import { useStudy } from "./context/StudyContext";

/** Legacy props type for tests that render StudyView with StudyProvider (StudyView itself takes no props). */
export type StudyViewProps = Record<string, never>;

export function StudyView() {
  const {
    decks,
    studyDecks,
    studyLevel,
    setStudyLevel,
    selectedDeckId,
    setSelectedDeckId,
    session,
    current,
    revealed,
    furiganaMode,
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
    sessionGoalReviews,
    setSessionGoalReviews,
    sessionGoalReached,
    setSessionGoalReached,
    sessionReviewsDone,
    userSettings,
    onSaveDailyGoal,
    onLoadDeckCards,
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
  } = useStudy();

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [dailyGoalInput, setDailyGoalInput] = useState<string>("");
  const [deckLabels, setDeckLabels] = useState<string[]>([]);
  const [liveAnnouncement, setLiveAnnouncement] = useState("");
  const hadSessionRef = useRef(false);
  const studyCardRegionRef = useRef<HTMLDivElement>(null);

  const activeCardId =
    session && current && current.kind !== "done" ? current.card.id : null;
  const [studyNoteBody, setStudyNoteBody] = useState<string | null>(null);
  const [studyNoteLoading, setStudyNoteLoading] = useState(false);
  const [studyNoteError, setStudyNoteError] = useState<string | null>(null);
  const [studyNoteSaving, setStudyNoteSaving] = useState(false);

  const reloadStudyNote = useCallback(() => {
    if (!activeCardId) return Promise.resolve();
    setStudyNoteLoading(true);
    setStudyNoteError(null);
    return fetchCardStudyNote(activeCardId)
      .then((r) => {
        setStudyNoteBody(r.body);
      })
      .catch((e: unknown) => {
        setStudyNoteError(e instanceof Error ? e.message : "Could not load note");
      })
      .finally(() => {
        setStudyNoteLoading(false);
      });
  }, [activeCardId]);

  useEffect(() => {
    if (!activeCardId) {
      setStudyNoteBody(null);
      setStudyNoteError(null);
      setStudyNoteLoading(false);
      return;
    }
    let cancelled = false;
    setStudyNoteLoading(true);
    setStudyNoteError(null);
    fetchCardStudyNote(activeCardId)
      .then((r) => {
        if (!cancelled) setStudyNoteBody(r.body);
      })
      .catch((e: unknown) => {
        if (!cancelled) setStudyNoteError(e instanceof Error ? e.message : "Could not load note");
      })
      .finally(() => {
        if (!cancelled) setStudyNoteLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeCardId]);

  const saveStudyNote = useCallback(
    async (body: string) => {
      if (!activeCardId) return;
      setStudyNoteSaving(true);
      setStudyNoteError(null);
      try {
        const r = await putCardStudyNote(activeCardId, body);
        setStudyNoteBody(r.body);
      } catch (e: unknown) {
        setStudyNoteError(e instanceof Error ? e.message : "Could not save note");
        throw e;
      } finally {
        setStudyNoteSaving(false);
      }
    },
    [activeCardId]
  );

  const deleteStudyNote = useCallback(async () => {
    if (!activeCardId) return;
    setStudyNoteSaving(true);
    setStudyNoteError(null);
    try {
      await deleteCardStudyNote(activeCardId);
      setStudyNoteBody(null);
    } catch (e: unknown) {
      setStudyNoteError(e instanceof Error ? e.message : "Could not delete note");
      throw e;
    } finally {
      setStudyNoteSaving(false);
    }
  }, [activeCardId]);

  useEffect(() => {
    const v = userSettings?.daily_goal_reviews;
    setDailyGoalInput(v != null && v > 0 ? String(v) : "");
  }, [userSettings?.daily_goal_reviews]);

  useEffect(() => {
    let cancelled = false;
    setDeckLabels([]);
    setStudyLabel(null);
    if (!selectedDeckId) return;
    fetchDeckLabels(selectedDeckId)
      .then((res) => {
        if (cancelled) return;
        setDeckLabels(res.labels ?? []);
      })
      .catch(() => {
        if (cancelled) return;
        setDeckLabels([]);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedDeckId, setStudyLabel]);

  // Announce session start, card position, and session complete for screen readers.
  useEffect(() => {
    if (!session || !current) {
      hadSessionRef.current = false;
      setLiveAnnouncement("");
      return;
    }
    const total = session.due_now + session.new_limit;
    if (current.kind === "done") {
      setLiveAnnouncement("Session complete.");
      hadSessionRef.current = true;
      return;
    }
    const remaining =
      (session.due_now - (current.kind === "due" || current.kind === "learning" ? 1 : 0)) +
      (current.new_remaining ?? session.new_limit);
    const done = Math.max(0, Math.min(total, total - remaining));
    // done matches the progress label (e.g. "1 / 7 cards" when viewing first card)
    if (!hadSessionRef.current) {
      setLiveAnnouncement(`Session started. Card ${done} of ${total}.`);
      hadSessionRef.current = true;
    } else {
      setLiveAnnouncement(`Card ${done} of ${total}.`);
    }
  }, [session, current]);

  // Move focus to the study card when session becomes active so keyboard/screen-reader users land on the card.
  useEffect(() => {
    if (!session || !current || current.kind === "done") return;
    const el = studyCardRegionRef.current;
    if (el) {
      const id = requestAnimationFrame(() => {
        el.focus();
      });
      return () => cancelAnimationFrame(id);
    }
  }, [session, current]);

  return (
    <section className="panel" aria-label="Study">
      <div
        role="status"
        aria-live="polite"
        aria-atomic
        className="sr-only"
        id="study-live-region"
      >
        {liveAnnouncement}
      </div>
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Study</div>
        </div>
      </div>

      <div className="studyDeckRow">
        <label className="label">
          Level
          <select className="input" value={studyLevel} onChange={(e) => setStudyLevel(e.target.value)} aria-label="Level">
            <option value="All">All</option>
            {["N5", "N4", "N3", "N2", "N1"].map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </label>

        <label className="label" style={{ flex: 1, minWidth: 120 }}>
          Deck
          <select
            className="input"
            value={selectedDeckId}
            onChange={async (e) => {
              const id = e.target.value;
              setSelectedDeckId(id);
              await onLoadDeckCards(id);
            }}
          >
            {!decks ? (
              <option value="">Loading…</option>
            ) : studyDecks.length === 0 ? (
              <option value="">No decks</option>
            ) : null}
            {studyDecks.map((d: Deck) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </label>

        <button
          type="button"
          className="button buttonSecondary studySettingsToggle"
          onClick={() => setSettingsOpen((v) => !v)}
          aria-expanded={settingsOpen}
          aria-controls="study-settings"
        >
          {settingsOpen ? "Hide settings" : "Settings"}
        </button>

        <button
          type="button"
          className="button buttonPrimary"
          onClick={onStartSession}
          disabled={!selectedDeckId || busy}
          aria-busy={busy && !session}
        >
          {busy && !session ? "Starting…" : "Start"}
        </button>
      </div>

      <div className="studyDeckRow">
        <label className="label" style={{ flex: 1, minWidth: 160 }}>
          Label
          <select
            className="input"
            value={studyLabel ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setStudyLabel(v || null);
            }}
            aria-label="Label"
          >
            <option value="">Select label…</option>
            {deckLabels.map((t) => {
              const name = t.startsWith("label:") ? t.slice("label:".length) : t;
              return (
                <option key={t} value={t}>
                  {name}
                </option>
              );
            })}
          </select>
        </label>

        <button
          className="button buttonPrimary"
          type="button"
          onClick={() => void onStartLabelSession()}
          disabled={!selectedDeckId || !studyLabel || busy}
          aria-busy={busy && !session}
        >
          {busy && !session ? "Starting…" : "Start label session"}
        </button>
      </div>

      {settingsOpen ? (
        <div id="study-settings" className="studySettingsDropdown">
          <div className="settingsSection">
            <span className="settingsLabel">Daily goal</span>
            <div className="settingsRow">
              <input
                type="number"
                className="input"
                min={0}
                max={500}
                value={dailyGoalInput}
                onChange={(e) => setDailyGoalInput(e.target.value)}
                placeholder="0"
                aria-label="Daily goal"
                style={{ width: 60 }}
              />
              <span className="muted">reviews</span>
              <button
                type="button"
                className="button buttonSecondary"
                onClick={() => {
                  const v = dailyGoalInput.trim();
                  if (v === "") onSaveDailyGoal(null);
                  else {
                    const n = parseInt(v, 10);
                    onSaveDailyGoal(Number.isFinite(n) && n >= 0 ? n : null);
                  }
                }}
              >
                Save
              </button>
            </div>
          </div>

          {!session ? (
            <div className="settingsSection">
              <span className="settingsLabel">Session target</span>
              <div className="settingsRow">
                <label className="settingsOption">
                  <input
                    type="radio"
                    name="sessionGoal"
                    checked={sessionGoalType === "none"}
                    onChange={() => setSessionGoalType("none")}
                  />
                  <span>None</span>
                </label>
                <label className="settingsOption">
                  <input
                    type="radio"
                    name="sessionGoal"
                    checked={sessionGoalType === "short_session"}
                    onChange={() => setSessionGoalType("short_session")}
                  />
                  <span>Short</span>
                </label>
                {sessionGoalType === "short_session" ? (
                  <>
                    <select
                      className="input"
                      value={sessionGoalShortCards}
                      onChange={(e) => setSessionGoalShortCards(Number(e.target.value))}
                      style={{ width: 56 }}
                    >
                      {[5, 10, 15, 20, 25, 30].map((n) => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                    <span className="muted">cards</span>
                  </>
                ) : null}
                <label className="settingsOption">
                  <input
                    type="radio"
                    name="sessionGoal"
                    checked={sessionGoalType === "session_goal"}
                    onChange={() => setSessionGoalType("session_goal")}
                  />
                  <span>Goal</span>
                </label>
                {sessionGoalType === "session_goal" ? (
                  <>
                    <input
                      type="number"
                      className="input"
                      min={5}
                      max={100}
                      value={sessionGoalReviews}
                      onChange={(e) => {
                        const n = parseInt(e.target.value, 10);
                        if (Number.isFinite(n) && n >= 5 && n <= 100) setSessionGoalReviews(n);
                      }}
                      style={{ width: 52 }}
                    />
                    <span className="muted">reviews</span>
                  </>
                ) : null}
              </div>
            </div>
          ) : null}

          <div className="settingsSection">
            <span className="settingsLabel">Options</span>
            <div className="settingsRow">
              <label className="settingsOption">
                <input type="checkbox" checked={catchUpMode} onChange={(e) => setCatchUpMode(e.target.checked)} />
                <span>Catch-up (no new)</span>
              </label>
              <label className="settingsOption">
                <input type="checkbox" checked={includeListening} onChange={(e) => setIncludeListening(e.target.checked)} />
                <span>Listening cards</span>
              </label>
            </div>
          </div>
        </div>
      ) : null}

      {decks && decks.length === 0 ? (
        <div className="emptyState">
          <div className="emptyTitle">No decks</div>
          <div className="emptySubtitle">Import a CSV to get started.</div>
          <div className="row" style={{ marginTop: 10, flexDirection: "row" }}>
            <button className="button buttonPrimary" onClick={() => setTab("import")}>Decks</button>
            <button className="button buttonSecondary" onClick={onRefreshDecks} disabled={busy}>Refresh</button>
          </div>
        </div>
      ) : null}

      {session ? (
        <>
          {sessionGoalReached ? (
            <div className="sessionGoalReachedBanner" role="status">
              <strong>Goal reached!</strong>
              <div className="row" style={{ marginTop: 10, gap: 8, flexDirection: "row" }}>
                <button className="button buttonPrimary" onClick={onEndSession}>End</button>
                <button className="button buttonSecondary" onClick={() => setSessionGoalReached(false)}>Continue</button>
              </div>
            </div>
          ) : null}
          <div className="sessionProgress" aria-label="Session summary">
            {sessionGoalType !== "none" ? (
              <div className="sessionProgressWrap sessionGoalProgress">
                <div className="sessionProgressLabel">
                  {sessionGoalType === "short_session" ? (
                    <><strong>{sessionReviewsDone}</strong> / {sessionGoalShortCards}</>
                  ) : (
                    <><strong>{sessionReviewsDone}</strong> / {sessionGoalReviews}</>
                  )}
                </div>
                <progress
                  className="sessionProgressNative"
                  value={sessionReviewsDone}
                  max={sessionGoalType === "short_session" ? sessionGoalShortCards : sessionGoalReviews}
                />
              </div>
            ) : null}
            {(() => {
              const total = session.due_now + session.new_limit;
              let done = 0;
              if (total > 0) {
                if (current?.kind === "done") {
                  done = total;
                } else {
                  const remaining =
                    (session.due_now - (current?.kind === "due" || current?.kind === "learning" ? 1 : 0)) +
                    (current?.new_remaining ?? session.new_limit);
                  done = Math.max(0, Math.min(total, total - remaining));
                }
              }
              return (
                <div className="sessionProgressWrap">
                  <div className="sessionProgressLabel">
                    <strong>{done}</strong> / {total} cards
                  </div>
                  <progress className="sessionProgressNative" value={done} max={total || 1} />
                </div>
              );
            })()}
            {(session.daily_goal_reviews != null && session.daily_goal_reviews > 0) ||
            (session.streak_days != null && session.streak_days > 0) ? (
              <div className="sessionDailyGoalRow">
                {session.daily_goal_reviews != null && session.daily_goal_reviews > 0 ? (
                  <span className="sessionDailyGoal">
                    <strong>{(session.reviews_done_today ?? 0) + sessionReviewsDone}</strong> / {session.daily_goal_reviews} today
                  </span>
                ) : null}
                {session.streak_days != null && session.streak_days > 0 ? (
                  <span className="sessionStreak">{session.streak_days}d streak</span>
                ) : null}
              </div>
            ) : null}
            <div className="sessionStatsRow">
              <span className="sessionStat sessionStatDue">
                <span className="sessionStatValue">{session.due_now}</span>
                <span className="sessionStatLabel">due</span>
              </span>
              <span className="sessionStat">
                <span className="sessionStatValue">{session.new_available}</span>
                <span className="sessionStatLabel">new</span>
              </span>
              <span className="sessionStat sessionStatEst">
                <span className="sessionStatValue">~{session.estimated_minutes}m</span>
                <span className="sessionStatLabel">est</span>
              </span>
            </div>
          </div>
        </>
      ) : null}

      <div style={{ marginTop: 12 }}>
        {!session ? null : !current ? (
          <div className="muted">Loading…</div>
        ) : current.kind === "done" ? (
          <div className="muted">Session complete.</div>
        ) : (
          <div
            ref={studyCardRegionRef}
            role="region"
            tabIndex={-1}
            aria-label="Current card"
          >
            <StudyCard
            current={current as StudyCardCurrent}
            revealed={revealed}
            furiganaMode={furiganaMode}
            busy={busy}
            hintsUsed={hintsUsed}
            answerSavedFlash={answerSavedFlash}
            answerSavedTotal={answerSavedTotal}
            audioError={audioError}
            autoPlayListening={autoPlayListening}
            onAutoPlayChange={(v: boolean) => {
              setAutoPlayListening(v);
              try {
                if (typeof localStorage !== "undefined")
                  localStorage.setItem("vocab_listening_autoplay", v ? "true" : "false");
              } catch {
                // ignore
              }
            }}
            onRevealToggle={onRevealToggle}
            onRate={onRate}
            onPlayAudio={onPlayAudio}
            onFuriganaChange={onFuriganaChange}
            studyFromExamples={studyFromExamples}
            onStudyFromExamplesChange={setStudyFromExamples}
            studyNote={{
              body: studyNoteBody,
              loading: studyNoteLoading,
              error: studyNoteError,
              saving: studyNoteSaving,
              onReload: () => {
                void reloadStudyNote();
              },
              onSave: saveStudyNote,
              onDelete: deleteStudyNote,
            }}
          />
          </div>
        )}
      </div>
    </section>
  );
}
