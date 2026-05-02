import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchSearchExamples,
  fetchUserSettings,
  importGenericVocab,
  importGrammar,
  importKanji,
  syncImport,
  type ImportResult,
  type SearchExamplesCard,
  type SyncImportResult,
  type SyncMergeExisting,
  type SyncSourceType,
} from "./api";
import { AccountDropdown, ErrorBoundary } from "./components";
import { StudyView } from "./StudyView";
import { StudyProvider } from "./context/StudyContext";
import { AppProvider } from "./context/AppContext";
import { useApp } from "./context/AppContext";
import { useAuth } from "./context/AuthContext";
import { LandingView } from "./views/LandingView";
import { SEARCH_RESULTS_LIMIT } from "./constants";
import {
  ImportTab,
  LeechesTab,
  MetricsTab,
  SearchTab,
} from "./tabs";

/** Auth gate: landing (login/register) when not authenticated; tabbed app when authenticated. */
export default function App() {
  const { isAuthenticated, authLoading } = useAuth();
  if (!isAuthenticated && !authLoading) {
    return <LandingView />;
  }
  if (authLoading) {
    return (
      <div className="page landingPage">
        <main id="main-content" className="landingMain">
          <div className="panel">
            <p className="muted">Loading…</p>
          </div>
        </main>
      </div>
    );
  }
  return (
    <AppProvider>
      <TabbedApp />
    </AppProvider>
  );
}

/** Tabbed main app (Study, Import, Decks, etc.). Only mounted when user is authenticated. */
function TabbedApp() {
  const {
    tab,
    setTab,
    decks,
    selectedDeckId,
    setSelectedDeckId,
    error,
    setError,
    busy,
    setBusy,
    onRefreshDecks,
    onLoadDeckCards,
  } = useApp();

  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [level, setLevel] = useState<string>("N5");
  const [deckName, setDeckName] = useState<string>("");
  const leechesSearchQueryRef = useRef<string | null>(null);
  const [searchExamplesQuery, setSearchExamplesQuery] = useState("");
  const [searchExamplesResults, setSearchExamplesResults] = useState<SearchExamplesCard[]>([]);
  const [searchExamplesLoading, setSearchExamplesLoading] = useState(false);
  const [searchExamplesError, setSearchExamplesError] = useState<string | null>(null);
  const [selectedExampleCard, setSelectedExampleCard] = useState<SearchExamplesCard | null>(null);
  const [syncResult, setSyncResult] = useState<SyncImportResult | null>(null);
  const [syncDeckId, setSyncDeckId] = useState<string>("");
  const [syncLevel, setSyncLevel] = useState<string>("N5");
  const [syncSourceType, setSyncSourceType] = useState<SyncSourceType>("grammar");
  const [syncFormat, setSyncFormat] = useState<string>("default");
  const [syncMergeExisting, setSyncMergeExisting] = useState<SyncMergeExisting>("skip");
  const [userSettings, setUserSettings] = useState<{ daily_goal_reviews: number | null } | null>(null);

  // Load user settings (e.g. daily goal) when opening Study tab
  useEffect(() => {
    if (tab !== "study") return;
    fetchUserSettings()
      .then((s) => setUserSettings({ daily_goal_reviews: s.daily_goal_reviews }))
      .catch(() => setUserSettings(null));
  }, [tab]);

  // When switching to examples from Leeches with a prefill query, run search once
  useEffect(() => {
    if (tab !== "examples" || !leechesSearchQueryRef.current) return;
    onSearchExamples();
    leechesSearchQueryRef.current = null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const handleLoadDeckCards = useCallback(
    async (deckId: string) => {
      setError(null);
      try {
        return await onLoadDeckCards(deckId);
      } catch {
        return null;
      }
    },
    [onLoadDeckCards, setError]
  );

  async function onSearchExamples() {
    setSearchExamplesError(null);
    setSearchExamplesLoading(true);
    setSelectedExampleCard(null);
    try {
      const res = await fetchSearchExamples(searchExamplesQuery, SEARCH_RESULTS_LIMIT);
      setSearchExamplesResults(res.cards);
    } catch (e: unknown) {
      setSearchExamplesError(e instanceof Error ? e.message : "Search failed");
      setSearchExamplesResults([]);
    } finally {
      setSearchExamplesLoading(false);
    }
  }

  async function onImportGrammar(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setError(null);
    setImportResult(null);
    const fileInput = (ev.currentTarget.elements.namedItem("grammarFile") as HTMLInputElement) || null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setError("Pick a grammar CSV file first.");
      return;
    }
    setBusy(true);
    try {
      const res = await importGrammar(file, level, deckName);
      setImportResult(res);
      await onRefreshDecks();
      setSelectedDeckId(res.deck_id);
      await handleLoadDeckCards(res.deck_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  async function onImportGenericVocab(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setError(null);
    setImportResult(null);
    const fileInput = (ev.currentTarget.elements.namedItem("vocabFile") as HTMLInputElement) || null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setError("Pick a vocab CSV file first.");
      return;
    }
    setBusy(true);
    try {
      const res = await importGenericVocab(file, level, deckName);
      setImportResult(res);
      await onRefreshDecks();
      setSelectedDeckId(res.deck_id);
      await handleLoadDeckCards(res.deck_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  async function onImportKanji(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setError(null);
    setImportResult(null);
    const fileInput = (ev.currentTarget.elements.namedItem("kanjiFile") as HTMLInputElement) || null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setError("Pick a kanji CSV file first.");
      return;
    }
    setBusy(true);
    try {
      const res = await importKanji(file, level, deckName);
      setImportResult(res);
      await onRefreshDecks();
      setSelectedDeckId(res.deck_id);
      await handleLoadDeckCards(res.deck_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  async function onSyncImport(ev: React.FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setError(null);
    setSyncResult(null);
    if (!syncDeckId) {
      setError("Select a deck to sync into.");
      return;
    }
    const fileInput = (ev.currentTarget.elements.namedItem("syncFile") as HTMLInputElement) || null;
    const file = fileInput?.files?.[0];
    if (!file) {
      setError("Pick a CSV file to sync.");
      return;
    }
    setBusy(true);
    try {
      const res = await syncImport(syncDeckId, syncLevel, syncSourceType, syncFormat, file, syncMergeExisting);
      setSyncResult(res);
      await onRefreshDecks();
      await handleLoadDeckCards(syncDeckId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="appHeader">
        <div>
          <div className="title">Furikaeri</div>
          <div className="subtitle">Local JLPT flashcards app</div>
        </div>

        <div className="headerRight">
          {busy ? <span className="muted">Working…</span> : null}
          <AccountDropdown />
        </div>
      </header>

      {error ? <div className="alert" role="alert">{error}</div> : null}

      <nav className="tabs" aria-label="Primary navigation">
        {(
          [
            ["study", "Study"],
            ["import", "Decks"],
            ["examples", "Search"],
            ["metrics", "Metrics"],
            ["leeches", "Leeches"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            className={tab === key ? `tab tab-${key} tabActive` : `tab tab-${key}`}
            onClick={() => setTab(key)}
            aria-current={tab === key ? "page" : undefined}
          >
            {label}
          </button>
        ))}
      </nav>

      <main id="main-content">
      {tab === "study" ? (
        <ErrorBoundary key="study" name="Study">
          <StudyProvider
            decks={decks}
            selectedDeckId={selectedDeckId}
            setSelectedDeckId={setSelectedDeckId}
            busy={busy}
            setBusy={setBusy}
            setError={setError}
            onRefreshDecks={onRefreshDecks}
            onLoadDeckCards={onLoadDeckCards}
            userSettings={userSettings}
            setUserSettings={setUserSettings}
            setTab={setTab}
          >
            <StudyView />
          </StudyProvider>
        </ErrorBoundary>
      ) : null}

      {tab === "import" ? (
        <ErrorBoundary key="import" name="Decks">
        <ImportTab
          level={level}
          setLevel={setLevel}
          deckName={deckName}
          setDeckName={setDeckName}
          importResult={importResult}
          setImportResult={setImportResult}
          syncResult={syncResult}
          setSyncResult={setSyncResult}
          syncDeckId={syncDeckId}
          setSyncDeckId={setSyncDeckId}
          syncLevel={syncLevel}
          setSyncLevel={setSyncLevel}
          syncSourceType={syncSourceType}
          setSyncSourceType={setSyncSourceType}
          syncFormat={syncFormat}
          setSyncFormat={setSyncFormat}
          syncMergeExisting={syncMergeExisting}
          setSyncMergeExisting={setSyncMergeExisting}
          onImportGrammar={onImportGrammar}
          onImportGenericVocab={onImportGenericVocab}
          onImportKanji={onImportKanji}
          onSyncImport={onSyncImport}
        />
        </ErrorBoundary>
      ) : null}

      {tab === "examples" ? (
        <ErrorBoundary key="examples" name="Search">
        <SearchTab
          searchExamplesQuery={searchExamplesQuery}
          setSearchExamplesQuery={setSearchExamplesQuery}
          searchExamplesResults={searchExamplesResults}
          setSearchExamplesResults={setSearchExamplesResults}
          searchExamplesLoading={searchExamplesLoading}
          setSearchExamplesLoading={setSearchExamplesLoading}
          searchExamplesError={searchExamplesError}
          setSearchExamplesError={setSearchExamplesError}
          selectedExampleCard={selectedExampleCard}
          setSelectedExampleCard={setSelectedExampleCard}
          onSearchExamples={onSearchExamples}
        />
        </ErrorBoundary>
      ) : null}

      {tab === "metrics" ? (
        <ErrorBoundary key="metrics" name="Metrics">
          <MetricsTab />
        </ErrorBoundary>
      ) : null}

      {tab === "leeches" ? (
        <ErrorBoundary key="leeches" name="Leeches">
        <LeechesTab
          onGoToSearch={(query: string) => {
            leechesSearchQueryRef.current = query;
            setSearchExamplesQuery(query);
            setTab("examples");
            setSelectedExampleCard(null);
          }}
        />
        </ErrorBoundary>
      ) : null}
      </main>
    </div>
  );
}

