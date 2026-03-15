import React from "react";
import type { SessionCard } from "./api";

export type FuriganaMode = "off" | "hover" | "on";

export type StudyCardCurrent = {
  kind: "due" | "new" | "learning";
  new_remaining: number;
  card: SessionCard;
};

export type StudyCardProps = {
  current: StudyCardCurrent;
  revealed: boolean;
  furiganaMode: FuriganaMode;
  busy: boolean;
  hintsUsed: number;
  answerSavedFlash: boolean;
  answerSavedTotal: number | null;
  audioError: string | null;
  autoPlayListening?: boolean;
  onAutoPlayChange?: (v: boolean) => void;
  onRevealToggle: () => void;
  onRate: (rating: "again" | "hard" | "good" | "easy") => void;
  onPlayAudio: () => void;
  onFuriganaChange: (mode: FuriganaMode) => void;
  studyFromExamples?: boolean;
  onStudyFromExamplesChange?: (v: boolean) => void;
};

/** Filter example entries to those with non-empty first line (same empty handling as kanji/grammar/vocab). */
export function filterNonEmptyExamples(examples: unknown[]): string[] {
  if (!Array.isArray(examples)) return [];
  return examples.filter((ex): ex is string => {
    const first = (typeof ex === "string" ? ex : "").split("\n")[0]?.trim() ?? "";
    return first.length > 0;
  });
}

/** Coerce unknown to string (avoids TS inferring {} from Record<string, unknown>). */
export function unknownToStr(x: unknown): string {
  return typeof x === "string" ? x : String(x ?? "");
}

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

/** Get text to speak for TTS. For vocab_listening uses front.tts_text; otherwise uses example-based candidates. */
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
