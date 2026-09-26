import type { CandidateMeta, RaceMeta } from "./types";

export type LikelyWinner = "Democratic" | "Republican" | "Toss-up";

export interface WinnerProbability {
  party: LikelyWinner;
  probability: number;
}

const wholeNumber = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
  minimumFractionDigits: 0,
});
const signedWholeNumber = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
  minimumFractionDigits: 0,
  signDisplay: "exceptZero",
});
const wholePercent = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 0,
  minimumFractionDigits: 0,
});
const wholeDollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
  minimumFractionDigits: 0,
});

function requireFinite(value: number): void {
  if (!Number.isFinite(value)) throw new Error("display value must be finite");
}

export function formatInteger(value: number): string {
  requireFinite(value);
  return wholeNumber.format(value);
}

export function formatSignedInteger(value: number, suffix = ""): string {
  requireFinite(value);
  return `${signedWholeNumber.format(value)}${suffix}`;
}

export function formatMargin(value: number): string {
  requireFinite(value);
  const rounded = Math.round(Math.abs(value));
  if (rounded === 0) return "Even";
  return `${value > 0 ? "Dem." : "Rep."} +${wholeNumber.format(rounded)} points`;
}

export function formatInterval(lower: number, upper: number): string {
  return `${formatInteger(lower)} to ${formatInteger(upper)}`;
}

export function formatPvi(value: number): string {
  requireFinite(value);
  const rounded = Math.round(value);
  if (rounded === 0) return "Even";
  return `${rounded > 0 ? "D" : "R"}+${wholeNumber.format(Math.abs(rounded))}`;
}

export function formatCandidate(candidate: CandidateMeta): string {
  const incumbent = candidate.is_incumbent ? "*" : "";
  return `${candidate.name}${incumbent} (${candidate.party}-${candidate.municipality})`;
}

export function formatPercent(probability: number): string {
  if (!Number.isFinite(probability) || probability < 0 || probability > 1) {
    throw new Error("probability must be between zero and one");
  }
  return wholePercent.format(probability);
}

export function formatProbabilityPointDelta(delta: number): string {
  return formatSignedInteger(delta * 100, " pts");
}

export function formatDollars(value: number): string {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error("receipt amount must be finite and non-negative");
  }
  return wholeDollars.format(value);
}

export function formatDollarInput(value: number): string {
  if (!Number.isFinite(value) || value < 0) {
    throw new Error("receipt amount must be finite and non-negative");
  }
  return wholeNumber.format(value);
}

export function parseDollarInput(text: string): number {
  const value = text.trim();
  const ungrouped = /^(0|[1-9]\d*)$/;
  const grouped = /^[1-9]\d{0,2}(,\d{3})+$/;
  if (!ungrouped.test(value) && !grouped.test(value)) {
    throw new Error("Candidate receipts must be non-negative whole dollars, with optional comma separators.");
  }
  const parsed = Number(value.replaceAll(",", ""));
  if (!Number.isSafeInteger(parsed) || parsed < 0) {
    throw new Error("Candidate receipts must be non-negative whole dollars, with optional comma separators.");
  }
  return parsed;
}

export function likelyWinner(democraticProbability: number): WinnerProbability {
  if (!Number.isFinite(democraticProbability) || democraticProbability < 0 || democraticProbability > 1) {
    throw new Error("probability must be between zero and one");
  }
  if (democraticProbability === 0.5) return { party: "Toss-up", probability: 0.5 };
  if (democraticProbability > 0.5) {
    return { party: "Democratic", probability: democraticProbability };
  }
  return { party: "Republican", probability: 1 - democraticProbability };
}

export function probabilityComparison(current: number, baseline: number): string {
  const currentWinner = likelyWinner(current);
  const baselineWinner = likelyWinner(baseline);
  if (currentWinner.party !== baselineWinner.party) {
    return `Favorite changes: ${baselineWinner.party} to ${currentWinner.party}`;
  }
  return formatProbabilityPointDelta(currentWinner.probability - baselineWinner.probability);
}

export function compareCompetitiveness(left: RaceMeta, right: RaceMeta): number {
  return Math.abs(left.published.point_margin) - Math.abs(right.published.point_margin)
    || left.office.localeCompare(right.office)
    || left.district_display.localeCompare(right.district_display, undefined, { numeric: true })
    || left.target_id.localeCompare(right.target_id);
}

export function racesByCompetitiveness(races: RaceMeta[]): RaceMeta[] {
  return [...races].sort(compareCompetitiveness);
}
