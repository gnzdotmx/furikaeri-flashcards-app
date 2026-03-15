import React from "react";
import { safeJson } from "../utils";
import { highlight, filterNonEmptyExamples } from "../studyCardUtils";
import type { SearchExamplesCard } from "../api";

export type SearchTabProps = {
  searchExamplesQuery: string;
  setSearchExamplesQuery: (q: string) => void;
  searchExamplesResults: SearchExamplesCard[];
  setSearchExamplesResults: (r: SearchExamplesCard[]) => void;
  searchExamplesLoading: boolean;
  setSearchExamplesLoading: (l: boolean) => void;
  searchExamplesError: string | null;
  setSearchExamplesError: (e: string | null) => void;
  selectedExampleCard: SearchExamplesCard | null;
  setSelectedExampleCard: (c: SearchExamplesCard | null) => void;
  onSearchExamples: () => Promise<void>;
};

export function SearchTab(props: SearchTabProps) {
  const {
    searchExamplesQuery,
    setSearchExamplesQuery,
    searchExamplesResults,
    searchExamplesLoading,
    searchExamplesError,
    selectedExampleCard,
    setSelectedExampleCard,
    onSearchExamples,
  } = props;

  if (selectedExampleCard) {
    const card = selectedExampleCard;
    const front = safeJson<Record<string, unknown>>(card.front_template) ?? {};
    const back = safeJson<Record<string, unknown>>(card.back_template) ?? {};
    const isKanji = card.card_type.startsWith("kanji_");
    const isGrammar = card.card_type.startsWith("grammar_");
    const isVocab = card.card_type.startsWith("vocab_");
    const isKanjiUsage = card.card_type === "kanji_usage";
    const target =
      (isKanji ? (front.kanji || back.kanji || front.target || "") : "") ||
      (isGrammar ? (front.expression || back.expression || "") : "") ||
      (isVocab ? (front.word || back.word || "") : "");
    const grammarExprJp = typeof target === "string" ? target.split("(")[0].trim() : "";
    const exampleFirstLine = front.example ? (String(front.example).split("\n")[0] || "").trim() : "";
    const kanjiUsageSentence = (isKanjiUsage && front.sentence_jp && String(front.sentence_jp).trim()) || "";
    return (
      <section className="panel">
        <div className="exampleDetail">
          <button type="button" className="button buttonSecondary" onClick={() => setSelectedExampleCard(null)} style={{ marginBottom: "1rem" }}>
            ← Back to list
          </button>
          <div className="studyShell" style={{ maxWidth: "100%" }}>
            <div className="pill pillType" style={{ marginBottom: 8 }}>{card.card_type}</div>
            {card.deck_name ? <div className="muted" style={{ marginBottom: 8 }}>Deck: {card.deck_name}</div> : null}
            {isKanjiUsage ? (
              <div className="exampleBlock" style={{ marginBottom: 10 }}>
                {kanjiUsageSentence ? (
                  <div className="jpText">{highlight(String(kanjiUsageSentence), front.target)}</div>
                ) : (
                  <div className="muted">(No sentence)</div>
                )}
                {(back.sentence_romaji || back.sentence_en) ? (
                  <>
                    {back.sentence_romaji ? <div className="romaji">{String(back.sentence_romaji)}</div> : null}
                    {back.sentence_en ? <div className="en">{String(back.sentence_en)}</div> : null}
                  </>
                ) : null}
              </div>
            ) : null}
            {isGrammar && (back.expression || front.example || front.expression) ? (
              <div className="exampleBlock" style={{ marginBottom: 10 }}>
                {back.expression ? <div className="jpWord" style={{ marginBottom: 6 }}>{String(back.expression)}</div> : front.expression ? <div className="jpWord" style={{ marginBottom: 6 }}>{String(front.expression)}</div> : null}
                {exampleFirstLine ? (
                  <>
                    <div className="jpText">{highlight(String(exampleFirstLine), grammarExprJp)}</div>
                    <div className="romaji">{String(front.example).split("\n")[1] || ""}</div>
                    <div className="en">{String(front.example).split("\n")[2] || ""}</div>
                  </>
                ) : (
                  <div className="muted">(No example)</div>
                )}
              </div>
            ) : null}
            {isGrammar && back.meaning ? <div className="enStrong">{String(back.meaning)}</div> : null}
            {isKanji && back.meaning ? <div className="enStrong">{String(back.meaning)}</div> : null}
            {isVocab && back.meaning ? <div className="enStrong">{String(back.meaning)}</div> : null}
            {back.structure ? <pre className="mono">{String(back.structure)}</pre> : null}
            {back.onyomi || back.kunyomi ? (
              <div className="row" style={{ marginTop: 8 }}>
                {back.onyomi ? <span className="badge">On: {String(back.onyomi)}</span> : null}
                {back.kunyomi ? <span className="badge">Kun: {String(back.kunyomi)}</span> : null}
              </div>
            ) : null}
            {(() => {
              const examples = filterNonEmptyExamples(Array.isArray(back.examples) ? back.examples : []);
              return examples.length > 0 ? (
                <div style={{ marginTop: 12 }}>
                  <div className="sectionTitle">Examples</div>
                  {examples.slice(0, 5).map((ex: string, i: number) => {
                    const lines = String(ex).split("\n");
                    const highlightTarget = typeof grammarExprJp === "string" ? grammarExprJp : (typeof target === "string" ? target : "");
                    return (
                      <div className="exampleBlock" key={i}>
                        <div className="jpText">{highlight(lines[0] || "", highlightTarget)}</div>
                        <div className="romaji">{lines[1] || ""}</div>
                        <div className="en">{lines[2] || ""}</div>
                      </div>
                    );
                  })}
                </div>
              ) : null;
            })()}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">Search examples</div>
          <div className="panelSubtitle">Search by word (English or Japanese); click a result to see grammar and examples</div>
        </div>
      </div>
      <div className="row" style={{ flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
        <input
          type="search"
          className="input"
          placeholder="Search by word (English or Japanese)"
          value={searchExamplesQuery}
          onChange={(e) => setSearchExamplesQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), onSearchExamples())}
          style={{ minWidth: "200px", flex: 1 }}
          aria-label="Search examples"
        />
        <button type="button" className="button buttonPrimary" onClick={onSearchExamples} disabled={searchExamplesLoading}>
          {searchExamplesLoading ? "Searching…" : "Search"}
        </button>
      </div>
      {searchExamplesError ? <div className="alert" role="alert">{searchExamplesError}</div> : null}
      {searchExamplesResults.length > 0 ? (
        <ul className="exampleList" style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {searchExamplesResults.map((card) => {
            const front = safeJson<Record<string, unknown>>(card.front_template) ?? {};
            const summary =
              (front.example && String(front.example).split("\n")[0]?.trim()) ||
              (front.expression && String(front.expression)) ||
              (front.word && String(front.word)) ||
              (front.kanji && String(front.kanji)) ||
              (front.sentence_jp && String(front.sentence_jp).trim()) ||
              card.card_type;
            return (
              <li key={card.id} style={{ marginBottom: "0.5rem" }}>
                <button
                  type="button"
                  className="button buttonSecondary"
                  style={{ width: "100%", display: "flex", textAlign: "left", justifyContent: "flex-start", alignItems: "center" }}
                  onClick={() => setSelectedExampleCard(card)}
                >
                  <span className="jpText" style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}>{String(summary)}</span>
                  {card.deck_name ? <span className="muted" style={{ fontSize: "0.85rem", marginLeft: 8 }}>{card.deck_name}</span> : null}
                </button>
              </li>
            );
          })}
        </ul>
      ) : searchExamplesQuery.trim() && !searchExamplesLoading ? (
        <p className="muted">No examples found. Try another word.</p>
      ) : null}
      {!searchExamplesQuery.trim() ? <p className="muted">Enter a word and press Search to find examples.</p> : null}
    </section>
  );
}
