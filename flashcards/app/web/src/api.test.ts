import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  startSession,
  fetchMetrics,
  answerCard,
  nextCard,
  deleteDeck,
  downloadDeckImportFormatCsv,
  setAuthToken,
} from "./api";

describe("startSession", () => {
  it("sends include_listening: false when option is false", async () => {
    let body: Record<string, unknown> = {};
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) => {
        body = init?.body ? JSON.parse(init.body as string) : {};
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              session_id: "test-session",
              deck: { id: "deck1", name: "Deck" },
              due_now: 0,
              due_today: 0,
              new_available: 0,
              new_limit: 0,
              estimated_minutes: 0,
            }),
        } as Response);
      })
    );
    await startSession("deck1", { include_listening: false });
    expect(body).toMatchObject({ deck_id: "deck1", include_listening: false });
    vi.unstubAllGlobals();
  });

  it("omits include_listening when option is true (default)", async () => {
    let body: Record<string, unknown> = {};
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) => {
        body = init?.body ? JSON.parse(init.body as string) : {};
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              session_id: "test-session",
              deck: { id: "deck1", name: "Deck" },
              due_now: 0,
              due_today: 0,
              new_available: 0,
              new_limit: 0,
              estimated_minutes: 0,
            }),
        } as Response);
      })
    );
    await startSession("deck1", { include_listening: true });
    expect(body.deck_id).toBe("deck1");
    expect(body).not.toHaveProperty("include_listening");
    vi.unstubAllGlobals();
  });
});

describe("fetchMetrics", () => {
  it("returns MetricsResponse with n, by_rating, again_rate, retention_proxy, avg_time_ms", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: new Headers({ "content-type": "application/json" }),
          text: () =>
            Promise.resolve(
              JSON.stringify({
                n: 10,
                by_rating: { again: 1, hard: 2, good: 5, easy: 2 },
                again_rate: 0.1,
                retention_proxy: 0.9,
                avg_time_ms: 5000,
              })
            ),
        } as Response)
      )
    );
    const res = await fetchMetrics();
    expect(res.n).toBe(10);
    expect(res.by_rating).toEqual({ again: 1, hard: 2, good: 5, easy: 2 });
    expect(res.again_rate).toBe(0.1);
    expect(res.retention_proxy).toBe(0.9);
    expect(res.avg_time_ms).toBe(5000);
    vi.unstubAllGlobals();
  });
});

describe("answerCard", () => {
  it("returns AnswerCardResponse with card_id and answer_submitted_total", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              ok: true,
              card_id: "c1",
              rating: "good",
              answer_submitted_total: 42,
            }),
        } as Response)
      )
    );
    const res = await answerCard("s1", "c1", "good", 3000, 0);
    expect(res.card_id).toBe("c1");
    expect(res.rating).toBe("good");
    expect(res.answer_submitted_total).toBe(42);
    vi.unstubAllGlobals();
  });
});

describe("nextCard", () => {
  it("returns card variant with SessionCard when not done", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              kind: "due",
              new_remaining: 5,
              card: {
                id: "card1",
                note_id: "n1",
                deck_id: "d1",
                card_type: "grammar_meaning_recognition",
                front_template: "{}",
                back_template: "{}",
                created_at: "2024-01-01T00:00:00Z",
              },
            }),
        } as Response)
      )
    );
    const res = await nextCard("session1");
    expect(res.kind).toBe("due");
    if (res.kind !== "done") {
      expect(res.card.id).toBe("card1");
      expect(res.card.card_type).toBe("grammar_meaning_recognition");
    }
    vi.unstubAllGlobals();
  });

  it("returns done variant", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ kind: "done" }),
        } as Response)
      )
    );
    const res = await nextCard("session1");
    expect(res.kind).toBe("done");
    vi.unstubAllGlobals();
  });
});

describe("downloadDeckImportFormatCsv", () => {
  beforeEach(() => {
    setAuthToken("test-token");
  });

  afterEach(() => {
    setAuthToken(null);
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("fetches with Bearer and credentials, then triggers anchor download", async () => {
    const blob = new Blob(["a,b"], { type: "text/csv" });
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: new Headers({
            "content-type": "text/csv",
            "Content-Disposition": 'attachment; filename="exp.csv"',
          }),
          blob: () => Promise.resolve(blob),
        } as Response)
      )
    );
    const objectUrl = "blob:mock-url";
    const createObjectURL = vi.fn(() => objectUrl);
    const revokeObjectURL = vi.fn();
    Object.defineProperty(globalThis.URL, "createObjectURL", {
      value: createObjectURL,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(globalThis.URL, "revokeObjectURL", {
      value: revokeObjectURL,
      configurable: true,
      writable: true,
    });

    const anchors: HTMLAnchorElement[] = [];
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string, options?: unknown) => {
      const el = origCreate(tag, options as never);
      if (tag === "a") anchors.push(el as HTMLAnchorElement);
      return el;
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await downloadDeckImportFormatCsv("deck-id-here", "My Deck");

    expect(fetch).toHaveBeenCalledWith(
      "/api/exports/decks/deck-id-here/cards.csv",
      expect.objectContaining({
        credentials: "include",
        headers: { Authorization: "Bearer test-token" },
      })
    );
    expect(anchors.length).toBe(1);
    expect(anchors[0].download).toBe("exp.csv");
    expect(anchors[0].href).toBe(objectUrl);
    expect(clickSpy).toHaveBeenCalled();
  });

  it("throws with JSON detail on error response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 404,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({ detail: "not found" }),
        } as Response)
      )
    );
    await expect(downloadDeckImportFormatCsv("missing", undefined)).rejects.toThrow("not found");
  });
});

describe("deleteDeck", () => {
  it("calls DELETE /api/decks/{deck_id} with auth + credentials", async () => {
    setAuthToken("test-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ deck_id: "d1", deleted: true }),
        } as Response)
      )
    );
    const res = await deleteDeck("d1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/decks/d1",
      expect.objectContaining({
        method: "DELETE",
        credentials: "include",
        headers: { Authorization: "Bearer test-token" },
      })
    );
    expect(res.deleted).toBe(true);
    setAuthToken(null);
    vi.unstubAllGlobals();
  });
});
