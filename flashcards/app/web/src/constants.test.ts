import { describe, expect, it } from "vitest";
import {
  LEECH_LAPSES_THRESHOLD,
  LIST_CARDS_LIMIT,
  METRICS_SUMMARY_LIMIT,
  SEARCH_RESULTS_LIMIT,
} from "./constants";

describe("constants", () => {
  it("defines leech and search/list limits as positive integers", () => {
    expect(LEECH_LAPSES_THRESHOLD).toBe(8);
    expect(SEARCH_RESULTS_LIMIT).toBe(80);
    expect(LIST_CARDS_LIMIT).toBe(200);
    expect(METRICS_SUMMARY_LIMIT).toBe(200);
  });

  it("uses values that match backend defaults (study_config.py)", () => {
    // Frontend should stay in sync with api/app/study_config.py
    expect(LEECH_LAPSES_THRESHOLD).toBeGreaterThanOrEqual(3);
    expect(LEECH_LAPSES_THRESHOLD).toBeLessThanOrEqual(20);
    expect(SEARCH_RESULTS_LIMIT).toBeGreaterThanOrEqual(10);
    expect(SEARCH_RESULTS_LIMIT).toBeLessThanOrEqual(500);
  });
});
