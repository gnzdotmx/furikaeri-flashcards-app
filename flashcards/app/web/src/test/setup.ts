import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Tell React we are in an act()-aware environment (removes "not configured to support act(...)" warning)
(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

afterEach(() => {
  cleanup();
});

// Mock fetch for component tests so AppProvider and App don't fail on mount
vi.stubGlobal(
  "fetch",
  vi.fn((url: string) => {
    if (url.includes("/api/health")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            status: "ok",
            db: { ok: true, path: "/data/db.sqlite", exists: true, writable_dir: true },
          }),
      } as Response);
    }
    if (url.includes("/api/decks")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ decks: [] }),
      } as Response);
    }
    if (url.includes("/api/users/settings")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            new_cards_per_day: 20,
            target_retention: 0.9,
            daily_goal_reviews: null,
          }),
      } as Response);
    }
    // Let other fetches fail (tests that need specific mocks will override)
    return Promise.reject(new Error("fetch not mocked"));
  })
);
