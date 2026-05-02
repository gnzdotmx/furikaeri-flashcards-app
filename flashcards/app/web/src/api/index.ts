/** API client: auth, decks, sessions, imports, metrics, tts. */

export { setAuthToken, authHeaders, isDev } from "./core";

export type { AuthUser, LoginResponse, RegisterResponse, HealthResponse } from "./auth";
export { loginApi, registerApi, fetchMe, logoutApi, fetchHealth } from "./auth";

export type {
  Deck,
  DeckCardsResponse,
  LeechCard,
  DeckLeechesResponse,
  DeckLabelsResponse,
  SearchExamplesCard,
  SearchExamplesResponse,
} from "./decks";
export {
  fetchDecks,
  deleteDeck,
  fetchDeckCards,
  fetchDeckLeeches,
  fetchDeckLabels,
  setCardSuspended,
  fetchSearchExamples,
} from "./decks";

export type { CardStudyNoteResponse } from "./cardStudyNote";
export { fetchCardStudyNote, putCardStudyNote, deleteCardStudyNote } from "./cardStudyNote";

export type {
  SessionStartResponse,
  SessionCard,
  NextCardResponse,
  AnswerCardResponse,
} from "./sessions";
export { startSession, nextCard, answerCard } from "./sessions";

export { logEvent } from "./events";

export { fetchTtsKana, tts } from "./tts";

export { downloadDeckImportFormatCsv } from "./exports";

export type { UserSettingsResponse } from "./users";
export { fetchUserSettings, updateUserSettings } from "./users";

export type { MetricsResponse } from "./metrics";
export { fetchMetrics } from "./metrics";

export type {
  ImportResult,
  SyncImportResult,
  SyncSourceType,
  SyncMergeExisting,
} from "./imports";
export { syncImport, importGrammar, importGenericVocab, importKanji } from "./imports";
