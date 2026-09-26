import type {
  ComponentAsset,
  Incumbency,
  NumericSupport,
  RaceInputs,
  ScenarioInputs,
  Summary,
} from "./types";

export function incumbencyIndicators(value: Incumbency): [number, number] {
  if (value === "No_Incumbent") return [0, 0];
  if (value === "Dem_Incumbent") return [1, 0];
  if (value === "GOP_Incumbent") return [0, 1];
  throw new Error(`unsupported incumbency ${String(value)}`);
}

export function receiptLogRatio(dem: number, opponent: number): number {
  if (!Number.isFinite(dem) || !Number.isFinite(opponent) || dem < 0 || opponent < 0) {
    throw new Error("Candidate receipts must be finite, non-negative amounts.");
  }
  return Math.log((dem + 1) / (opponent + 1));
}

export function quantile(values: number[], probability: number): number {
  if (values.length === 0) throw new Error("cannot summarize an empty draw array");
  const sorted = [...values].sort((left, right) => left - right);
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  const fraction = position - lower;
  return sorted[lower] + (sorted[upper] - sorted[lower]) * fraction;
}

export function summarize(values: number[]): Summary {
  if (values.length === 0 || values.some((value) => !Number.isFinite(value))) {
    throw new Error("draws must be a non-empty finite array");
  }
  return {
    point_margin: values.reduce((total, value) => total + value, 0) / values.length,
    lower_90: quantile(values, 0.05),
    upper_90: quantile(values, 0.95),
    dem_win_probability: values.filter((value) => value > 0).length / values.length,
  };
}

export function scenarioDraws(
  publishedDraws: number[],
  published: RaceInputs,
  scenario: ScenarioInputs,
  component: ComponentAsset,
): number[] {
  const [publishedDem, publishedGop] = incumbencyIndicators(published.incumbent_status);
  const [scenarioDem, scenarioGop] = incumbencyIndicators(scenario.incumbent_status);
  const demCoefficient = component.terms.incumbent_dem;
  const gopCoefficient = component.terms.incumbent_gop;
  if (!demCoefficient || !gopCoefficient) {
    throw new Error(`${component.component} is missing incumbency coefficient draws`);
  }
  const allArrays = [publishedDraws, demCoefficient, gopCoefficient];
  if (allArrays.some((values) => values.length !== publishedDraws.length)) {
    throw new Error("scenario draw arrays have inconsistent lengths");
  }
  let moneyDelta = 0;
  let moneyCoefficient: number[] | null = null;
  if (published.money_predictor) {
    if (scenario.dem_receipts === null || scenario.opponent_receipts === null || published.money_logratio === null) {
      throw new Error("finance component requires both candidate receipt amounts");
    }
    moneyCoefficient = component.terms[published.money_predictor];
    if (!moneyCoefficient || moneyCoefficient.length !== publishedDraws.length) {
      throw new Error(`${component.component} is missing aligned money coefficient draws`);
    }
    moneyDelta = receiptLogRatio(scenario.dem_receipts, scenario.opponent_receipts) - published.money_logratio;
  }
  return publishedDraws.map((draw, index) =>
    draw
    + (scenarioDem - publishedDem) * demCoefficient[index]
    + (scenarioGop - publishedGop) * gopCoefficient[index]
    + (moneyCoefficient ? moneyDelta * moneyCoefficient[index] : 0),
  );
}

export function outsideSupport(value: number, support?: NumericSupport): string | null {
  if (!support) return null;
  if (value < support.minimum || value > support.maximum) {
    return `The scenario value ${value.toFixed(3)} is outside the historical range ${support.minimum.toFixed(3)} to ${support.maximum.toFixed(3)}.`;
  }
  return null;
}

export function initialScenario(inputs: RaceInputs): ScenarioInputs {
  return {
    incumbent_status: inputs.incumbent_status,
    dem_receipts: inputs.dem_receipts,
    opponent_receipts: inputs.opponent_receipts,
  };
}
