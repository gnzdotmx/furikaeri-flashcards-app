import { describe, expect, it, vi } from "vitest";
import {
  startSession,
  fetchMetrics,
  answerCard,
  nextCard,
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
