import { describe, expect, it } from "vitest";
import golden from "../../tests/fixtures/interactive_scenarios.json";
import {
  initialScenario,
  outsideSupport,
  receiptLogRatio,
  scenarioDraws,
  summarize,
  withScenarioIncumbency,
  withScenarioReceipt,
} from "./scenario";
import type { ComponentAsset, Incumbency, RaceInputs } from "./types";

const component: ComponentAsset = {
  schema_version: 1,
  component: "fixture",
  predictors: ["PVI_N", "incumbent_status", "money_logratio_wide"],
  terms: golden.terms,
  numeric_support: { money_logratio_wide: { minimum: -2, maximum: 2 } },
  categorical_support: {
    incumbent_status: {
      No_Incumbent: 10,
      Dem_Incumbent: 20,
      GOP_Incumbent: 5,
    },
  },
};

function inputs(money: boolean): RaceInputs {
  return {
    PVI_N: 1,
    incumbent_status: "No_Incumbent",
    dem_receipts: money ? 0 : null,
    opponent_receipts: money ? 0 : null,
    money_predictor: money ? "money_logratio_wide" : null,
    money_logratio: money ? 0 : null,
  };
}

describe("scenario calculations", () => {
  it("leaves unchanged draws exactly unchanged", () => {
    const published = inputs(false);
    expect(scenarioDraws(golden.published_draws, published, initialScenario(published), component)).toEqual(golden.published_draws);
  });

  it("matches every shared Python golden scenario", () => {
    for (const testCase of golden.cases) {
      const hasMoney = testCase.money_predictor !== null;
      const published = inputs(hasMoney);
      const scenario = initialScenario(published);
      scenario.incumbent_status = testCase.scenario_incumbency as Incumbency;
      if (hasMoney) {
        scenario.dem_receipts = Math.E - 1;
        scenario.opponent_receipts = 0;
      }
      const actual = scenarioDraws(golden.published_draws, published, scenario, component);
      actual.forEach((value, index) => expect(value).toBeCloseTo(testCase.expected_draws[index], 12));
      const summary = summarize(actual);
      for (const [name, expected] of Object.entries(testCase.expected_summary)) {
        expect(summary[name as keyof typeof summary]).toBeCloseTo(expected, 12);
      }
    }
  });

  it("validates receipts and reports extrapolation", () => {
    expect(() => receiptLogRatio(-1, 0)).toThrow(/non-negative/);
    expect(outsideSupport(3, { minimum: -2, maximum: 2 })).toMatch(/outside/);
    expect(outsideSupport(1, { minimum: -2, maximum: 2 })).toBeNull();
  });

  it("resets state from immutable published inputs", () => {
    const published = {
      ...inputs(true),
      dem_receipts: 1000.4,
      opponent_receipts: 999.6,
    };
    const changed = initialScenario(published);
    changed.dem_receipts = 500;
    expect(initialScenario(published)).toEqual({
      incumbent_status: "No_Incumbent",
      dem_receipts: 1000.4,
      opponent_receipts: 999.6,
    });
  });

  it("updates one scenario field without reparsing rounded receipt displays", () => {
    const exact = initialScenario({
      ...inputs(true),
      dem_receipts: 1000.4,
      opponent_receipts: 999.6,
    });
    expect(withScenarioIncumbency(exact, "Dem_Incumbent")).toEqual({
      incumbent_status: "Dem_Incumbent",
      dem_receipts: 1000.4,
      opponent_receipts: 999.6,
    });
    expect(withScenarioReceipt(exact, "dem_receipts", 2500)).toEqual({
      incumbent_status: "No_Incumbent",
      dem_receipts: 2500,
      opponent_receipts: 999.6,
    });
  });
});
