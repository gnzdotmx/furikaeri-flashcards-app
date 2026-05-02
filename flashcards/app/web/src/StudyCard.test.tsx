import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { StudyCard } from "./StudyCard";
import type { StudyCardCurrent } from "./studyCardUtils";

/** Minimal SessionCard-like shape for tests (front/back are JSON strings). */
function makeCard(
  cardType: string,
  front: Record<string, unknown>,
  back: Record<string, unknown>
): StudyCardCurrent {
  return {
    kind: "new",
    new_remaining: 5,
    card: {
      id: "card-1",
      note_id: "note-1",
      deck_id: "deck-1",
      card_type: cardType,
      front_template: JSON.stringify(front),
      back_template: JSON.stringify(back),
      created_at: "2024-01-01T00:00:00Z",
    },
  };
}

const defaultHandlers = {
  onRevealToggle: vi.fn(),
  onRate: vi.fn(),
  onPlayAudio: vi.fn(),
  onFuriganaChange: vi.fn(),
};

describe("StudyCard", () => {
  it("renders grammar card with expression and example", () => {
    const current = makeCard(
      "grammar_meaning_recognition",
      { expression: "ことにする", example: "毎日勉強することにした。\nmainichi benkyou...\nI decided to study every day." },
      { meaning: "to decide to" }
    );
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("ことにする")).toBeInTheDocument();
    expect(screen.getByText(/毎日勉強することにした/)).toBeInTheDocument();
    expect(screen.getByText("Press Space or \"Reveal answer\".")).toBeInTheDocument();
  });

  it("renders vocab card with word and reading", () => {
    const current = makeCard(
      "vocab_meaning_recall",
      { word: "勉強", reading_kana: "べんきょう" },
      { word: "勉強", reading_kana: "べんきょう", meaning: "study" }
    );
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="hover"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("勉強")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /furigana mode/i })).toBeInTheDocument();
  });

  it("renders vocab card with word and example on front when example present (grammar-like)", () => {
    const exampleBlock = "毎日勉強する。\nmainichi benkyou suru.\nI study every day.";
    const current = makeCard(
      "vocab_meaning_recall",
      { word: "勉強", reading_kana: "べんきょう", example: exampleBlock },
      { word: "勉強", reading_kana: "べんきょう", meaning: "study", examples: [exampleBlock] }
    );
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    // Word at top, example sentence below (front shows only Japanese line, no romaji/en/prompt/pos).
    expect(screen.getAllByText("勉強").length).toBeGreaterThanOrEqual(1);
    const exampleNodes = screen.getAllByText(
      (_, el) => (el?.textContent?.trim() ?? "") === "毎日勉強する。"
    );
    expect(exampleNodes.length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("Recall reading (kana).")).not.toBeInTheDocument();
    expect(screen.getByText("study")).toBeInTheDocument();
    expect(screen.getByText(/Examples/)).toBeInTheDocument();
  });

  it("renders vocab front with word and (No example) when no example", () => {
    const current = makeCard(
      "vocab_reading_recall",
      { word: "悪魔", reading_kana: "あくま", pos: "Noun" },
      { word: "悪魔", reading_kana: "あくま", meaning: "devil", examples: [] }
    );
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("悪魔")).toBeInTheDocument();
    expect(screen.getByText("(No example)")).toBeInTheDocument();
    expect(screen.queryByText("Recall reading (kana).")).not.toBeInTheDocument();
    expect(screen.queryByText("Noun")).not.toBeInTheDocument();
  });

  it("renders vocab front without duplicate example or prompt (clean layout)", () => {
    const exampleBlock = "悪魔のような人。\nakuma no you na hito.\nA person like a devil.";
    const current = makeCard(
      "vocab_reading_recall",
      { word: "悪魔", reading_kana: "あくま", pos: "Noun", prompt: "Recall reading (kana).", example: exampleBlock },
      { word: "悪魔", reading_kana: "あくま", meaning: "devil", examples: [exampleBlock] }
    );
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getAllByText("悪魔").length).toBeGreaterThanOrEqual(1);
    const exampleSentenceNodes = screen.getAllByText(
      (_, el) => (el?.textContent?.trim() ?? "") === "悪魔のような人。"
    );
    expect(exampleSentenceNodes.length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("Recall reading (kana).")).not.toBeInTheDocument();
    expect(screen.queryByText("Noun")).not.toBeInTheDocument();
    expect(screen.queryByText("akuma no you na hito.")).not.toBeInTheDocument();
    expect(screen.queryByText("A person like a devil.")).not.toBeInTheDocument();
    expect(exampleSentenceNodes.length).toBeGreaterThanOrEqual(1);
  });

  it("renders kanji card with kanji and meaning", () => {
    const current = makeCard(
      "kanji_meaning_recognition",
      { kanji: "学" },
      { meaning: "study", kunyomi: "まな.ぶ", onyomi: "ガク" }
    );
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("学")).toBeInTheDocument();
    expect(screen.getByText("study")).toBeInTheDocument();
    expect(screen.getByText(/On:/)).toBeInTheDocument();
    expect(screen.getByText(/Kun:/)).toBeInTheDocument();
  });

  it("renders listening card with listen prompt when not revealed", () => {
    const current = makeCard(
      "vocab_listening",
      { tts_text: "べんきょう", prompt: "Recall the word." },
      { word: "勉強", meaning: "study" }
    );
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText(/Recall the word and meaning/)).toBeInTheDocument();
    const listenButtons = screen.getAllByRole("button", { name: /listen to word/i });
    expect(listenButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("calls onRevealToggle when Reveal button is clicked", () => {
    const onRevealToggle = vi.fn();
    const current = makeCard("grammar_meaning_recognition", { expression: "test" }, { meaning: "test" });
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        onRevealToggle={onRevealToggle}
        onRate={defaultHandlers.onRate}
        onPlayAudio={defaultHandlers.onPlayAudio}
        onFuriganaChange={defaultHandlers.onFuriganaChange}
      />
    );
    const revealBtn = screen.getByRole("button", { name: /reveal or hide answer/i });
    fireEvent.click(revealBtn);
    expect(onRevealToggle).toHaveBeenCalledTimes(1);
  });

  it("calls onRate with rating when Again/Hard/Good/Easy clicked", () => {
    const onRate = vi.fn();
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        onRevealToggle={defaultHandlers.onRevealToggle}
        onRate={onRate}
        onPlayAudio={defaultHandlers.onPlayAudio}
        onFuriganaChange={defaultHandlers.onFuriganaChange}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /rate good/i }));
    expect(onRate).toHaveBeenCalledWith("good");
    fireEvent.click(screen.getByRole("button", { name: /rate again/i }));
    expect(onRate).toHaveBeenCalledWith("again");
  });

  it("calls onFuriganaChange when furigana select changes", () => {
    const onFuriganaChange = vi.fn();
    const current = makeCard("vocab_meaning_recall", { word: "日" }, { meaning: "day" });
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="hover"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        onRevealToggle={defaultHandlers.onRevealToggle}
        onRate={defaultHandlers.onRate}
        onPlayAudio={defaultHandlers.onPlayAudio}
        onFuriganaChange={onFuriganaChange}
      />
    );
    const select = screen.getByRole("combobox", { name: /furigana mode/i });
    fireEvent.change(select, { target: { value: "on" } });
    expect(onFuriganaChange).toHaveBeenCalledWith("on");
  });

  it("calls onPlayAudio when Play button is clicked", () => {
    const onPlayAudio = vi.fn();
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        onRevealToggle={defaultHandlers.onRevealToggle}
        onRate={defaultHandlers.onRate}
        onPlayAudio={onPlayAudio}
        onFuriganaChange={defaultHandlers.onFuriganaChange}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /play audio/i }));
    expect(onPlayAudio).toHaveBeenCalledTimes(1);
  });

  it("shows audio error when audioError is set", () => {
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    render(
      <StudyCard
        current={current}
        revealed={false}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError="Playback failed."
        {...defaultHandlers}
      />
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Playback failed.");
  });

  it("disables rating and reveal buttons when busy", () => {
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={true}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByRole("button", { name: /reveal or hide/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /rate again/i })).toBeDisabled();
  });

  it("shows rating buttons with keyboard shortcut aria-labels", () => {
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByRole("button", { name: /rate again \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rate hard \(2\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rate good \(3\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /rate easy \(4\)/i })).toBeInTheDocument();
  });

  it("shows Saved status when answerSavedFlash is true", () => {
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={true}
        answerSavedTotal={42}
        audioError={null}
        {...defaultHandlers}
      />
    );
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Saved");
    expect(status).toHaveTextContent("42");
  });

  it("handles empty front template gracefully", () => {
    const current = makeCard("grammar_meaning_recognition", {}, { meaning: "only back" });
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("Back")).toBeInTheDocument();
    expect(screen.getByText("only back")).toBeInTheDocument();
  });

  it("renders My note panel with Add note when studyNote is provided and empty", () => {
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    const studyNote = {
      body: null,
      loading: false,
      error: null,
      saving: false,
      onReload: vi.fn(),
      onSave: vi.fn().mockResolvedValue(undefined),
      onDelete: vi.fn().mockResolvedValue(undefined),
    };
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        studyNote={studyNote}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("My note")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add note/i })).toBeInTheDocument();
  });

  it("shows deck CSV note on back when revealed", () => {
    const current = makeCard(
      "vocab_meaning_recall",
      { word: "試す", reading_kana: "ためす" },
      { word: "試す", reading_kana: "ためす", meaning: "to try", notes: "Line1\nLine2" }
    );
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("Deck note")).toBeInTheDocument();
    expect(screen.getByText(/Line1/)).toBeInTheDocument();
    expect(screen.getByText(/Line2/)).toBeInTheDocument();
  });

  it("shows saved note with edit and delete when studyNote has body", () => {
    const current = makeCard("grammar_meaning_recognition", { expression: "x" }, { meaning: "y" });
    const studyNote = {
      body: "Recall: 〜ことにする",
      loading: false,
      error: null,
      saving: false,
      onReload: vi.fn(),
      onSave: vi.fn().mockResolvedValue(undefined),
      onDelete: vi.fn().mockResolvedValue(undefined),
    };
    render(
      <StudyCard
        current={current}
        revealed={true}
        furiganaMode="off"
        busy={false}
        hintsUsed={0}
        answerSavedFlash={false}
        answerSavedTotal={null}
        audioError={null}
        studyNote={studyNote}
        {...defaultHandlers}
      />
    );
    expect(screen.getByText("Recall: 〜ことにする")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /edit note/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete note/i })).toBeInTheDocument();
  });
});
