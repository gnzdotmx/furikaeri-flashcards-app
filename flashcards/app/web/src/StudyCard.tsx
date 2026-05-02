import React, { useEffect, useState } from "react";
import { safeJson } from "./utils";
import type { StudyCardProps } from "./studyCardUtils";

/** Aligned with API limit (study_config import max cell chars default). */
const STUDY_NOTE_MAX_CHARS = 20_000;

export type FuriganaMode = "off" | "hover" | "on";

/** Examples with non-empty first line (matches backend empty handling). */
// eslint-disable-next-line react-refresh/only-export-components
export function filterNonEmptyExamples(examples: unknown[]): string[] {
  if (!Array.isArray(examples)) return [];
  return examples.filter((ex): ex is string => {
    const first = (typeof ex === "string" ? ex : "").split("\n")[0]?.trim() ?? "";
    return first.length > 0;
  });
}

function extractKana(reading: string): string[] {
  const m = reading.match(/[\u3040-\u30ffー]+/g);
  if (!m) return [];
  const out: string[] = [];
  for (const s of m) {
    const t = s.trim();
    if (t && !out.includes(t)) out.push(t);
  }
  return out;
}

/** Coerce to string for display. */
// eslint-disable-next-line react-refresh/only-export-components
export function unknownToStr(x: unknown): string {
  return typeof x === "string" ? x : String(x ?? "");
}

// eslint-disable-next-line react-refresh/only-export-components
export function highlight(text: string, target: unknown): React.ReactNode {
  const targetStr = unknownToStr(target);
  if (!text || !targetStr) return text;
  const parts = text.split(targetStr);
  if (parts.length === 1) return text;
  const nodes: React.ReactNode[] = [];
  parts.forEach((p, idx) => {
    nodes.push(p);
    if (idx < parts.length - 1) nodes.push(<mark key={`${idx}-${targetStr}`} className="mark">{targetStr}</mark>);
  });
  return <>{nodes}</>;
}

/** TTS text: front.tts_text for vocab_listening, else example-based. */
// eslint-disable-next-line react-refresh/only-export-components
export function getTtsTextForCard(
  card: { card_type: string },
  front: Record<string, unknown>,
  back: Record<string, unknown>
): string {
  const firstLine = (s: unknown): string =>
    (typeof s === "string" ? s : "").split("\n")[0]?.trim() ?? "";
  if (card.card_type === "vocab_listening") {
    const tts = (front.tts_text != null && String(front.tts_text).trim()) || "";
    if (tts) return tts;
  }
  const exampleCandidates: string[] = [];
  if (front.example) exampleCandidates.push(firstLine(front.example));
  if (front.sentence_jp) exampleCandidates.push(firstLine(front.sentence_jp));
  const nonEmptyExamples = filterNonEmptyExamples(Array.isArray(back.examples) ? back.examples : []);
  for (const ex of nonEmptyExamples) {
    const jp = firstLine(ex);
    if (jp) exampleCandidates.push(jp);
  }
  if (back.example) exampleCandidates.push(firstLine(back.example));
  return (exampleCandidates.find((s) => Boolean(s)) || "").trim();
}

/** Furigana: hover via mouse events + span (works without ruby/rt). */
function FuriganaWord({
  word,
  reading,
  mode,
  className = "",
}: {
  word: string;
  reading: string;
  mode: FuriganaMode;
  className?: string;
}) {
  const [hovered, setHovered] = useState(false);
  const hasReading = Boolean(reading && reading.trim());
  if (!hasReading) return <span className={`jpText ${className}`.trim()}>{word}</span>;
  if (mode === "off") return <span className={`jpText ${className}`.trim()}>{word}</span>;
  const showReading = mode === "on" || (mode === "hover" && hovered);
  return (
    <span
      className={`furigana-js-wrap ${className}`.trim()}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onTouchEnd={(e) => {
        if (mode === "hover") {
          e.preventDefault();
          setHovered((v) => !v);
        }
      }}
    >
      <span className="jpText furigana-base">{word}</span>
      {showReading ? <span className="furigana-reading">{reading}</span> : null}
    </span>
  );
}

export function StudyCard({
  current,
  revealed,
  furiganaMode,
  busy,
  hintsUsed,
  answerSavedFlash,
  answerSavedTotal,
  audioError,
  autoPlayListening = false,
  onAutoPlayChange,
  onRevealToggle,
  onRate,
  onPlayAudio,
  onFuriganaChange,
  studyFromExamples = false,
  onStudyFromExamplesChange,
  studyNote,
}: StudyCardProps) {
  const card = current.card;
  const [noteComposing, setNoteComposing] = useState(false);
  const [noteDraft, setNoteDraft] = useState("");

  useEffect(() => {
    setNoteComposing(false);
    setNoteDraft("");
  }, [card.id]);

  function beginAddNote() {
    setNoteDraft("");
    setNoteComposing(true);
  }

  function beginEditNote() {
    setNoteDraft(studyNote?.body ?? "");
    setNoteComposing(true);
  }

  async function submitNote() {
    if (!studyNote) return;
    const t = noteDraft.trim();
    if (!t) return;
    try {
      await studyNote.onSave(t);
      setNoteComposing(false);
      setNoteDraft("");
    } catch {
      /* error shown via studyNote.error */
    }
  }

  async function removeNote() {
    if (!studyNote) return;
    if (!window.confirm("Delete your note for this card?")) return;
    try {
      await studyNote.onDelete();
      setNoteComposing(false);
      setNoteDraft("");
    } catch {
      /* error shown via studyNote.error */
    }
  }
  const front = safeJson<Record<string, unknown>>(card.front_template) ?? {};
  const back = safeJson<Record<string, unknown>>(card.back_template) ?? {};

  const isKanji = card.card_type.startsWith("kanji_");
  const isGrammar = card.card_type.startsWith("grammar_");
  const isVocab = card.card_type.startsWith("vocab_");
  const isListeningCard = card.card_type === "vocab_listening";

  const target =
    (isKanji ? (front.kanji || back.kanji || front.target || "") : "") ||
    (isGrammar ? (front.expression || back.expression || "") : "") ||
    (isVocab ? (front.word || back.word || "") : "");

  const grammarExprJp = typeof target === "string" ? target.split("(")[0].trim() : "";
  const exampleFirstLine = front.example ? (String(front.example).split("\n")[0] || "").trim() : "";
  const isKanjiUsage = card.card_type === "kanji_usage";
  const kanjiUsageSentence = (isKanjiUsage && front.sentence_jp && String(front.sentence_jp).trim()) || "";
  const grammarExpression = (isGrammar && front.expression && String(front.expression).trim()) || "";
  // Never show rank or empty: if front.word is digits-only or empty, use back word/reading or front reading
  const frontWordStr = String(front.word ?? "").trim();
  const isFrontWordNumericOrEmpty = isVocab && (/^\d+$/.test(frontWordStr) || frontWordStr === "");
  const displayWordRaw = isFrontWordNumericOrEmpty
    ? String(back.word ?? back.reading_kana ?? front.reading_kana ?? "").trim()
    : frontWordStr || String(front.reading_kana ?? "").trim();
  const displayWord = /^\d+$/.test(displayWordRaw) ? String(back.reading_kana ?? back.word ?? "").trim() : displayWordRaw;
  const displayReading = isFrontWordNumericOrEmpty ? "" : String(front.reading_kana ?? "").trim();
  const vocabWord = (isVocab && (front.word != null || front.reading_kana != null || back.word != null || back.reading_kana != null))
    ? (displayWord || String(front.reading_kana || "").trim() || String(back.reading_kana || "").trim())
    : "";
  const vocabPromptOrTts = (isVocab && (String(front.prompt || "").trim() || String(front.tts_text || "").trim())) || "";
  const backExamplesList = filterNonEmptyExamples(Array.isArray(back.examples) ? back.examples : []);
  const vocabExampleLine =
    isVocab && studyFromExamples && backExamplesList[0]
      ? String(backExamplesList[0]).split("\n")[0]?.trim() ?? ""
      : "";
  const vocabFrontExample =
    isVocab && front.example != null && String(front.example).trim() ? String(front.example).trim() : "";
  const frontHasContent =
    (isKanji && !!String(front.kanji || "").trim()) ||
    (isKanjiUsage && !!kanjiUsageSentence) ||
    (isVocab && !!(vocabWord || vocabPromptOrTts || vocabExampleLine || vocabFrontExample)) ||
    (isGrammar && !!(exampleFirstLine || grammarExpression)) ||
    (!isGrammar && !isVocab && (!!String(front.expression || "").trim() || !!String(front.pos || "").trim() || !!String(front.prompt || "").trim() || !!String(front.example || "").trim()));

  const ttsText = getTtsTextForCard(card, front, back);

  /** Hide pos when rank-like or on vocab front (keep front: word + example only). */
  const posStr: string = front.pos != null ? String(front.pos).trim() : "";
  const rankStr = String((front as Record<string, unknown>).rank ?? "").trim();
  const showPosBadge =
    !isGrammar &&
    !isVocab &&
    posStr !== "" &&
    posStr !== rankStr &&
    !Number.isFinite(Number(posStr)) &&
    !/^\d+$/.test(posStr);

  return (
    <div className="studyShell">
      <div className="studyTop">
        <div className={`pill pill-${current.kind}`}>{current.kind.toUpperCase()}</div>
        <div className="pill pillType">{card.card_type}</div>
        <div className="spacer" />
        <label className="label">
          Furigana
          <select
            className="input"
            aria-label="Furigana mode"
            value={furiganaMode}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
              const v = e.target.value as FuriganaMode;
              onFuriganaChange(v);
            }}
          >
            <option value="off">Off</option>
            <option value="hover">Hover</option>
            <option value="on">On</option>
          </select>
        </label>

        {isVocab && onStudyFromExamplesChange ? (
          <label className="label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={studyFromExamples}
              onChange={(e) => onStudyFromExamplesChange(e.target.checked)}
              aria-label="Study from examples (front: example sentence; back: word, reading, meaning, examples)"
            />
            <span>Study from examples</span>
          </label>
        ) : null}

        {isListeningCard && onAutoPlayChange ? (
          <label className="label" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={autoPlayListening}
              onChange={(e) => onAutoPlayChange(e.target.checked)}
              aria-label="Auto-play listening cards"
            />
            <span className="muted" style={{ fontSize: "0.85rem" }}>Auto-play</span>
          </label>
        ) : null}

        <button
          className={`button ${isListeningCard ? "buttonPrimary" : "buttonSecondary"}`}
          onClick={onPlayAudio}
          aria-label={isListeningCard ? "Listen to word" : "Play audio"}
          style={isListeningCard ? { minWidth: 100 } : undefined}
        >
          {isListeningCard ? "Listen" : "Play"}
        </button>
      </div>

      {audioError ? <div className="alert" role="alert">{audioError}</div> : null}

      <div className="studyCard">
        {frontHasContent ? (
          <>
            <div className="side">
              <div className="sideTitle">Front</div>

              {isKanji && front.kanji ? (
                <div className="jpKanji">
                  <FuriganaWord word={String(front.kanji)} reading={extractKana(String(back.kunyomi || ""))[0] || ""} mode={furiganaMode} />
                </div>
              ) : null}

              {isKanjiUsage ? (
                <>
                  {front.prompt ? <div className="muted" style={{ marginBottom: 8 }}>{String(front.prompt)}</div> : null}
                  {kanjiUsageSentence ? (
                    <div className="exampleBlock">
                      <div className="jpText">{highlight(String(kanjiUsageSentence), front.target)}</div>
                    </div>
                  ) : (
                    <div className="muted">(No sentence)</div>
                  )}
                </>
              ) : null}

              {isVocab ? (
                isListeningCard ? (
                  <>
                    <div className="listenPrompt" style={{ marginBottom: 12, fontSize: "1.05rem" }}>
                      Recall the word and meaning.
                    </div>
                    {ttsText ? (
                      <button
                        type="button"
                        className="button buttonPrimary"
                        onClick={onPlayAudio}
                        aria-label="Listen to word"
                        style={{ padding: "10px 24px", fontSize: "1rem" }}
                      >
                        Listen
                      </button>
                    ) : null}
                  </>
                ) : (
                  (() => {
                    // Same structure as grammar: word at top, one example line below (no romaji/en on front, no prompt/pos)
                    const vocabExampleBlock =
                      (front.example != null && String(front.example).trim()) ||
                      (studyFromExamples && backExamplesList[0] ? String(backExamplesList[0]).trim() : "");
                    const vocabExampleFirstLine = vocabExampleBlock ? (String(vocabExampleBlock).split("\n")[0] || "").trim() : "";
                    const vocabHighlightTarget = grammarExprJp || (typeof target === "string" ? target : "") || displayWord;
                    return (
                      <>
                        {vocabWord ? (
                          <div className="jpWord" style={{ marginBottom: 6 }}>
                            <FuriganaWord word={displayWord} reading={displayReading} mode={furiganaMode} />
                          </div>
                        ) : (
                          <div className="muted">(No word)</div>
                        )}
                        {vocabExampleFirstLine ? (
                          <div className="exampleBlock">
                            <div className="jpText">{highlight(vocabExampleFirstLine, vocabHighlightTarget)}</div>
                          </div>
                        ) : (
                          <div className="muted">(No example)</div>
                        )}
                      </>
                    );
                  })()
                )
              ) : null}

              {isGrammar && grammarExpression ? <div className="jpWord" style={{ marginBottom: 6 }}>{String(grammarExpression)}</div> : null}
              {!isGrammar && !isVocab && front.expression ? <div className="jpWord">{String(front.expression)}</div> : null}

              {/* Part-of-speech badge: never show on grammar/vocab front (keep front clean); never show rank. */}
              {showPosBadge ? <span className="badge">{unknownToStr(front.pos).trim()}</span> : null}

              {!isGrammar && !isVocab && !isKanjiUsage && front.prompt && !isListeningCard ? <div className="muted">{String(front.prompt)}</div> : null}

              {isGrammar ? (
                exampleFirstLine ? (
                  <div className="exampleBlock">
                    <div className="jpText">{highlight(String(exampleFirstLine), grammarExprJp)}</div>
                  </div>
                ) : (
                  <div className="muted">(No example)</div>
                )
              ) : !isVocab && front.example ? (
                <div className="exampleBlock">
                  <div className="jpText">{highlight(String(front.example).split("\n")[0] || "", grammarExprJp)}</div>
                  <div className="romaji">{String(front.example).split("\n")[1] || ""}</div>
                  <div className="en">{String(front.example).split("\n")[2] || ""}</div>
                </div>
              ) : null}
            </div>

            <div className="divider" />
          </>
        ) : null}

        <div className="side">
          <div className="sideTitle">Back</div>

          {!revealed ? <div className="muted">Press Space or &quot;Reveal answer&quot;.</div> : null}

          {revealed ? (
            <>
              {isGrammar && (back.expression || front.example) ? (
                <div className="exampleBlock" style={{ marginBottom: 10 }}>
                  {back.expression ? <div className="jpWord" style={{ marginBottom: 6 }}>{String(back.expression)}</div> : null}
                  {front.example ? (
                    <>
                      <div className="romaji">{String(front.example).split("\n")[1] || ""}</div>
                      <div className="en">{String(front.example).split("\n")[2] || ""}</div>
                    </>
                  ) : null}
                </div>
              ) : null}
              {isGrammar && back.meaning ? <div className="enStrong">{String(back.meaning)}</div> : null}
              {isKanji && back.meaning ? <div className="enStrong">{String(back.meaning)}</div> : null}
              {isVocab ? (
                <div className="vocabBackBlock">
                  {(() => {
                    const backWord = String(back.word ?? "").trim();
                    const backReading = String(back.reading_kana ?? "").trim();
                    const isBackWordRankOrEmpty = backWord === "" || /^\d+$/.test(backWord);
                    const showWord = backWord || backReading;
                    const displayBackWord = isBackWordRankOrEmpty ? backReading : backWord;
                    const displayBackReading = isBackWordRankOrEmpty ? "" : backReading;
                    if (!showWord && displayBackWord === "") return null;
                    return (
                      <>
                        <div className="jpWord" style={{ marginBottom: 6 }}>
                          <FuriganaWord word={displayBackWord || backReading} reading={displayBackReading} mode={furiganaMode} />
                        </div>
                        {backReading && backReading !== backWord ? (
                          <div className="muted" style={{ marginBottom: 6 }}>Reading: {backReading}</div>
                        ) : null}
                      </>
                    );
                  })()}
                  {back.meaning != null && String(back.meaning).trim() !== "" ? (
                    <div className="enStrong">{String(back.meaning).trim()}</div>
                  ) : null}
                </div>
              ) : null}

              {isKanjiUsage && (back.sentence_romaji || back.sentence_en) ? (
                <div className="exampleBlock" style={{ marginTop: 8 }}>
                  {back.sentence_romaji ? <div className="romaji">{String(back.sentence_romaji)}</div> : null}
                  {back.sentence_en ? <div className="en">{String(back.sentence_en)}</div> : null}
                </div>
              ) : null}

              {back.structure ? <pre className="mono">{String(back.structure)}</pre> : null}

              {back.notes != null && String(back.notes).trim() !== "" ? (
                <div className="deckCsvNoteBlock">
                  <div className="sectionTitle">Deck note</div>
                  <pre className="deckCsvNoteBody">{String(back.notes)}</pre>
                </div>
              ) : null}

              {back.onyomi || back.kunyomi ? (
                <div className="row">
                  {back.onyomi ? <span className="badge">On: {String(back.onyomi)}</span> : null}
                  {back.kunyomi ? <span className="badge">Kun: {String(back.kunyomi)}</span> : null}
                </div>
              ) : null}

              {(() => {
                const examples = filterNonEmptyExamples(Array.isArray(back.examples) ? back.examples : []);
                const maxExamples = isVocab && studyFromExamples ? 20 : 3;
                return examples.length > 0 ? (
                  <div>
                    <div className="sectionTitle" style={{ marginTop: 10 }}>
                      Examples
                    </div>
                    {examples.slice(0, maxExamples).map((ex: string, i: number) => {
                      const lines = String(ex).split("\n");
                      return (
                        <div className="exampleBlock" key={i}>
                          <div className="jpText">{highlight(lines[0] || "", grammarExprJp || (typeof target === "string" ? target : ""))}</div>
                          <div className="romaji">{lines[1] || ""}</div>
                          <div className="en">{lines[2] || ""}</div>
                        </div>
                      );
                    })}
                  </div>
                ) : null;
              })()}
            </>
          ) : null}
        </div>
      </div>

      <div className="row">
        <button
          className="button buttonPrimary"
          onClick={onRevealToggle}
          aria-label="Reveal or hide answer"
          disabled={busy}
        >
          {revealed ? "Hide answer (Space)" : "Reveal answer (Space)"}
        </button>
        <div className="ratingButtonsGroup" aria-label="Keyboard shortcuts: 1 Again, 2 Hard, 3 Good, 4 Easy">
          <button className="button buttonAgain" onClick={() => onRate("again")} aria-label="Rate Again (1)" disabled={busy}>
            Again
          </button>
          <button className="button buttonHard" onClick={() => onRate("hard")} aria-label="Rate Hard (2)" disabled={busy}>
            Hard
          </button>
          <button className="button buttonGood" onClick={() => onRate("good")} aria-label="Rate Good (3)" disabled={busy}>
            Good
          </button>
          <button className="button buttonEasy" onClick={() => onRate("easy")} aria-label="Rate Easy (4)" disabled={busy}>
            Easy
          </button>
          <span className="ratingShortcutHint">1</span>
          <span className="ratingShortcutHint">2</span>
          <span className="ratingShortcutHint">3</span>
          <span className="ratingShortcutHint">4</span>
        </div>
        <span className="muted">Hints used: {hintsUsed}</span>
      </div>
      {answerSavedFlash ? (
        <p className="muted" style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "var(--color-success, green)" }} role="status">
          Saved{answerSavedTotal != null ? ` (${answerSavedTotal})` : ""}
        </p>
      ) : null}

      {studyNote ? (
        <div className="studyCardNote" aria-label="Your note for this card">
          <div className="studyCardNoteHeader">
            <span className="studyCardNoteTitle">My note</span>
            {studyNote.loading ? <span className="muted studyCardNoteStatus">Loading…</span> : null}
            {!studyNote.loading && studyNote.error ? (
              <span className="studyCardNoteError" role="alert">
                {studyNote.error}
                <button type="button" className="button buttonSecondary studyCardNoteRetry" onClick={() => studyNote.onReload()}>
                  Retry
                </button>
              </span>
            ) : null}
          </div>

          {!studyNote.loading && !studyNote.error ? (
            <>
              {noteComposing ? (
                <div className="studyCardNoteCompose">
                  <textarea
                    className="input studyCardNoteTextarea"
                    value={noteDraft}
                    onChange={(e) => setNoteDraft(e.target.value.slice(0, STUDY_NOTE_MAX_CHARS))}
                    maxLength={STUDY_NOTE_MAX_CHARS}
                    placeholder="Write a personal note (mnemonics, context, reminders)…"
                    aria-label="Note text"
                    rows={5}
                  />
                  <div className="studyCardNoteActions">
                    <button
                      type="button"
                      className="button buttonPrimary"
                      disabled={studyNote.saving || !noteDraft.trim()}
                      onClick={() => void submitNote()}
                    >
                      {studyNote.saving ? "Saving…" : "Save note"}
                    </button>
                    <button
                      type="button"
                      className="button buttonSecondary"
                      disabled={studyNote.saving}
                      onClick={() => {
                        setNoteComposing(false);
                        setNoteDraft("");
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                  <div className="muted studyCardNoteCounter">
                    {noteDraft.length} / {STUDY_NOTE_MAX_CHARS}
                  </div>
                </div>
              ) : studyNote.body != null && studyNote.body.trim() !== "" ? (
                <div className="studyCardNoteRead">
                  <pre className="studyCardNoteBody">{studyNote.body}</pre>
                  <div className="studyCardNoteActions">
                    <button type="button" className="button buttonSecondary" disabled={studyNote.saving} onClick={() => beginEditNote()}>
                      Edit note
                    </button>
                    <button type="button" className="button buttonSecondary" disabled={studyNote.saving} onClick={() => void removeNote()}>
                      Delete note
                    </button>
                  </div>
                </div>
              ) : (
                <div className="studyCardNoteEmpty">
                  <button type="button" className="button buttonSecondary" disabled={studyNote.saving} onClick={() => beginAddNote()}>
                    Add note
                  </button>
                </div>
              )}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
