import { describe, expect, it } from "vitest";
import {
  districtDetailsUrl,
  formatCandidate,
  formatDollarInput,
  formatDollars,
  formatInteger,
  formatInterval,
  formatMargin,
  formatPercent,
  formatProbabilityPointDelta,
  formatPvi,
  likelyWinner,
  parseDollarInput,
  probabilityComparison,
  racesByCompetitiveness,
} from "./presentation";
import type { RaceMeta } from "./types";

function race(targetId: string, margin: number, office = "State Representative", district = "1st Example"): RaceMeta {
  return {
    target_id: targetId,
    election_date: "2026-11-03",
    office,
    district,
    district_display: district,
    dem_candidate: { name: "Democrat", party: "D", municipality: "Pepperell", is_incumbent: false },
    comparison_candidate: { name: "Republican", party: "R", municipality: "Example", is_incumbent: false },
    component: "model",
    asset: `races/${targetId}.json`,
    published: { point_margin: margin, lower_90: -1, upper_90: 1, dem_win_probability: 0.5 },
    inputs: {
      PVI_N: 0,
      incumbent_status: "No_Incumbent",
      dem_receipts: 1000.4,
      opponent_receipts: 999.6,
      money_predictor: "money",
      money_logratio: 0,
    },
    support: [],
  };
}

describe("whole-unit presentation", () => {
  it("rounds reader-facing values without mutating their source", () => {
    const value = 1234.6;
    expect(formatInteger(value)).toBe("1,235");
    expect(formatInterval(-3.6, 8.4)).toBe("-4 to 8");
    expect(formatMargin(2.6)).toBe("Dem. +3 points");
    expect(formatMargin(-2.6)).toBe("Rep. +3 points");
    expect(formatMargin(0.4)).toBe("Even");
    expect(formatPvi(4.6)).toBe("D+5");
    expect(formatPvi(-1.6)).toBe("R+2");
    expect(formatPvi(0.4)).toBe("Even");
    expect(formatPercent(0.604)).toBe("60%");
    expect(formatProbabilityPointDelta(-0.016)).toBe("-2 pts");
    expect(formatDollars(1234567.8)).toBe("$1,234,568");
    expect(formatDollarInput(1234567.8)).toBe("1,234,568");
    expect(value).toBe(1234.6);
  });

  it("formats candidate identity and incumbent status", () => {
    expect(formatCandidate({ name: "Margaret R. Scarsdale", party: "D", municipality: "Pepperell", is_incumbent: true }))
      .toBe("Margaret R. Scarsdale* (D-Pepperell)");
    expect(formatCandidate({ name: "Alex Republican", party: "R", municipality: "Amesbury", is_incumbent: false }))
      .toBe("Alex Republican (R-Amesbury)");
  });

  it("links House and Senate races to their MAPOLI district pages", () => {
    expect(districtDetailsUrl(race("house", 1, "State Representative", "Ninth Norfolk")))
      .toBe("https://mapoli.us/districts/state-rep/ninth-norfolk.html");
    expect(districtDetailsUrl(race("senate", 1, "State Senate", "Worcester & Hampshire")))
      .toBe("https://mapoli.us/districts/state-senate/worcester-and-hampshire.html");
  });

  it("rejects non-finite or out-of-range display values", () => {
    expect(() => formatInteger(Number.NaN)).toThrow(/finite/);
    expect(() => formatPercent(1.1)).toThrow(/between/);
    expect(() => formatDollars(-1)).toThrow(/non-negative/);
  });
});

describe("likely-winner presentation", () => {
  it("shows the favored party or an exact toss-up", () => {
    expect(likelyWinner(0.64)).toEqual({ party: "Democratic", probability: 0.64 });
    expect(likelyWinner(0.4)).toEqual({ party: "Republican", probability: 0.6 });
    expect(likelyWinner(0.5)).toEqual({ party: "Toss-up", probability: 0.5 });
  });

  it("compares the same party and names favorite changes", () => {
    expect(probabilityComparison(0.7, 0.6)).toBe("+10 pts");
    expect(probabilityComparison(0.3, 0.4)).toBe("+10 pts");
    expect(probabilityComparison(0.6, 0.4)).toBe("Favorite changes: Republican to Democratic");
    expect(probabilityComparison(0.5, 0.5)).toBe("0 pts");
  });
});

describe("receipt input", () => {
  it("accepts grouped and ungrouped whole dollars", () => {
    expect(parseDollarInput("0")).toBe(0);
    expect(parseDollarInput("1000")).toBe(1000);
    expect(parseDollarInput("1,000")).toBe(1000);
    expect(parseDollarInput(" 12,345,678 ")).toBe(12345678);
  });

  it.each(["", "-1", "1.5", "1,00", "1,000.00", "1 000", "Infinity", "01"])(
    "rejects malformed value %s",
    (value) => expect(() => parseDollarInput(value)).toThrow(/whole dollars/),
  );
});

describe("race ordering", () => {
  it("uses full-precision competitiveness before deterministic ties", () => {
    const races = [
      race("rounded-tie-later", 1.49, "State Senate", "2nd Example"),
      race("closest", -0.51),
      race("rounded-tie-earlier", 1.41, "State Senate", "10th Example"),
      race("exact-tie-b", 2, "State Senate", "2nd Example"),
      race("exact-tie-a", -2, "State Senate", "2nd Example"),
    ];
    expect(racesByCompetitiveness(races).map((item) => item.target_id)).toEqual([
      "closest",
      "rounded-tie-earlier",
      "rounded-tie-later",
      "exact-tie-a",
      "exact-tie-b",
    ]);
    expect(races.map((item) => item.target_id)).toEqual([
      "rounded-tie-later",
      "closest",
      "rounded-tie-earlier",
      "exact-tie-b",
      "exact-tie-a",
    ]);
  });
});
