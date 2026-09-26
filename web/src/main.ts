import "./style.css";
import { renderDistribution } from "./chart";
import { BundleClient } from "./data";
import {
  initialScenario,
  outsideSupport,
  receiptLogRatio,
  scenarioDraws,
  summarize,
} from "./scenario";
import type { ComponentAsset, Incumbency, RaceAsset, RaceMeta, ScenarioInputs, Summary } from "./types";

function required<T extends Element>(selector: string): T {
  const value = document.querySelector<T>(selector);
  if (!value) throw new Error(`missing application element ${selector}`);
  return value;
}

const raceSelect = required<HTMLSelectElement>("#race-select");
const incumbency = required<HTMLSelectElement>("#incumbency");
const demReceipts = required<HTMLInputElement>("#dem-receipts");
const opponentReceipts = required<HTMLInputElement>("#opponent-receipts");
const reset = required<HTMLButtonElement>("#reset");
const inputError = required<HTMLElement>("#input-error");
const supportWarning = required<HTMLElement>("#support-warning");
const scenarioStatus = required<HTMLElement>("#scenario-status");
const explorer = required<HTMLElement>("#explorer");

let currentRace: RaceMeta;
let currentRaceAsset: RaceAsset;
let currentComponent: ComponentAsset;
let currentScenario: ScenarioInputs;
let loadSequence = 0;

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });

function margin(value: number): string {
  const rounded = Math.abs(value).toFixed(1);
  if (Math.abs(value) < 0.05) return "Even";
  return value > 0 ? `D +${rounded}` : `Opponent +${rounded}`;
}

function signed(value: number, suffix = ""): string {
  const rounded = value.toFixed(1);
  return `${value > 0 ? "+" : ""}${rounded}${suffix}`;
}

function summaryMarkup(summary: Summary, comparison?: Summary): string {
  const marginDelta = comparison ? signed(summary.point_margin - comparison.point_margin, " pts") : "";
  const probabilityDelta = comparison ? signed((summary.dem_win_probability - comparison.dem_win_probability) * 100, " pts") : "";
  return `
    <div class="stat"><span class="stat__label">Point margin</span><strong>${margin(summary.point_margin)}</strong>${comparison ? `<small>${marginDelta}</small>` : ""}</div>
    <div class="stat"><span class="stat__label">90% interval</span><strong>${summary.lower_90.toFixed(1)} to ${summary.upper_90.toFixed(1)}</strong></div>
    <div class="stat"><span class="stat__label">Democratic win</span><strong>${percent.format(summary.dem_win_probability)}</strong>${comparison ? `<small>${probabilityDelta}</small>` : ""}</div>
  `;
}

function isChanged(): boolean {
  const original = currentRace.inputs;
  return currentScenario.incumbent_status !== original.incumbent_status
    || currentScenario.dem_receipts !== original.dem_receipts
    || currentScenario.opponent_receipts !== original.opponent_receipts;
}

function readScenario(): ScenarioInputs {
  const finance = currentRace.inputs.money_predictor !== null;
  return {
    incumbent_status: incumbency.value as Incumbency,
    dem_receipts: finance ? demReceipts.valueAsNumber : null,
    opponent_receipts: finance ? opponentReceipts.valueAsNumber : null,
  };
}

function recalculate(): void {
  try {
    currentScenario = readScenario();
    const draws = scenarioDraws(currentRaceAsset.draws, currentRace.inputs, currentScenario, currentComponent);
    const scenarioSummary = summarize(draws);
    const changed = isChanged();
    required<HTMLElement>("#scenario-summary").innerHTML = summaryMarkup(
      scenarioSummary,
      changed ? currentRace.published : undefined,
    );
    scenarioStatus.textContent = changed ? "Hypothetical" : "Matches published";
    scenarioStatus.classList.toggle("status-pill--changed", changed);
    inputError.hidden = true;

    let warning: string | null = null;
    if (currentRace.inputs.money_predictor && currentScenario.dem_receipts !== null && currentScenario.opponent_receipts !== null) {
      const value = receiptLogRatio(currentScenario.dem_receipts, currentScenario.opponent_receipts);
      warning = outsideSupport(value, currentComponent.numeric_support[currentRace.inputs.money_predictor]);
    }
    supportWarning.hidden = warning === null;
    supportWarning.textContent = warning || "";
    renderDistribution(required<HTMLElement>("#chart"), currentRaceAsset.draws, draws);
  } catch (error) {
    inputError.textContent = error instanceof Error ? error.message : String(error);
    inputError.hidden = false;
  }
}

function renderRaceContext(race: RaceMeta): void {
  required<HTMLElement>("#race-context").innerHTML = `
    <p class="matchup"><strong>${race.dem_candidate_name}</strong><span>vs.</span><strong>${race.comparison_candidate_name}</strong></p>
    <p>${race.office} · ${race.district_display}</p>
  `;
  required<HTMLElement>("#published-summary").innerHTML = summaryMarkup(race.published);
  required<HTMLElement>("#published-inputs").innerHTML = `
    <div><dt>District PVI</dt><dd>${signed(race.inputs.PVI_N)}</dd></div>
    <div><dt>Incumbency</dt><dd>${race.inputs.incumbent_status.replaceAll("_", " ")}</dd></div>
    <div><dt>Democratic receipts</dt><dd>${race.inputs.dem_receipts === null ? "Not used" : money.format(race.inputs.dem_receipts)}</dd></div>
    <div><dt>Opponent receipts</dt><dd>${race.inputs.opponent_receipts === null ? "Not used" : money.format(race.inputs.opponent_receipts)}</dd></div>
  `;
}

async function selectRace(client: BundleClient, targetId: string): Promise<void> {
  const sequence = ++loadSequence;
  explorer.setAttribute("aria-busy", "true");
  const manifest = client.getManifest();
  const race = manifest.races.find((candidate) => candidate.target_id === targetId);
  if (!race) throw new Error(`unknown race ${targetId}`);
  const [raceAsset, component] = await Promise.all([
    client.loadRace(targetId),
    client.loadComponent(race.component),
  ]);
  if (sequence !== loadSequence) return;
  currentRace = race;
  currentRaceAsset = raceAsset;
  currentComponent = component;
  currentScenario = initialScenario(race.inputs);
  renderRaceContext(race);
  incumbency.value = race.inputs.incumbent_status;
  const hasFinance = race.inputs.money_predictor !== null;
  demReceipts.disabled = !hasFinance;
  opponentReceipts.disabled = !hasFinance;
  demReceipts.value = race.inputs.dem_receipts === null ? "" : String(race.inputs.dem_receipts);
  opponentReceipts.value = race.inputs.opponent_receipts === null ? "" : String(race.inputs.opponent_receipts);
  required<HTMLElement>("#finance-note").textContent = hasFinance
    ? `Receipts measured at the ${manifest.horizon} cutoff (${manifest.finance_cutoff}). The model uses their log ratio.`
    : "Fundraising controls are unavailable because this race uses the no-finance fallback component; scenarios do not switch components.";
  const counts = component.categorical_support.incumbent_status;
  required<HTMLElement>("#incumbency-support").textContent = `${counts[race.inputs.incumbent_status]} training races used the published incumbency level.`;
  recalculate();
  explorer.setAttribute("aria-busy", "false");
}

async function start(): Promise<void> {
  const baseUrl = `${import.meta.env.BASE_URL}data/2026/60d`.replace(/\/$/, "");
  const client = await BundleClient.load(baseUrl);
  const manifest = client.getManifest();
  const races = [...manifest.races].sort((left, right) =>
    left.office.localeCompare(right.office) || left.district_display.localeCompare(right.district_display, undefined, { numeric: true }),
  );
  raceSelect.replaceChildren(...races.map((race) => {
    const option = document.createElement("option");
    option.value = race.target_id;
    option.textContent = `${race.office.replace("State ", "")} — ${race.district_display}`;
    return option;
  }));
  required<HTMLAnchorElement>("#snapshot-link").href = manifest.source_snapshot_url;
  required<HTMLElement>("#provenance").innerHTML = `
    <div><dt>Forecast horizon</dt><dd>${manifest.horizon} · cutoff ${manifest.finance_cutoff}</dd></div>
    <div><dt>Training cutoff</dt><dd>${manifest.training_cutoff}</dd></div>
    <div><dt>Model</dt><dd><code>${manifest.variant}</code></dd></div>
    <div><dt>Definition</dt><dd><code>${manifest.definition}</code></dd></div>
    <div><dt>Source revision</dt><dd><code>${manifest.source_code_commit.slice(0, 12)}</code></dd></div>
  `;
  raceSelect.addEventListener("change", () => void selectRace(client, raceSelect.value));
  for (const control of [incumbency, demReceipts, opponentReceipts]) {
    control.addEventListener("input", recalculate);
  }
  incumbency.addEventListener("change", () => {
    const counts = currentComponent.categorical_support.incumbent_status;
    required<HTMLElement>("#incumbency-support").textContent = `${counts[incumbency.value as Incumbency]} training races used this incumbency level.`;
  });
  reset.addEventListener("click", () => {
    incumbency.value = currentRace.inputs.incumbent_status;
    demReceipts.value = currentRace.inputs.dem_receipts === null ? "" : String(currentRace.inputs.dem_receipts);
    opponentReceipts.value = currentRace.inputs.opponent_receipts === null ? "" : String(currentRace.inputs.opponent_receipts);
    currentScenario = initialScenario(currentRace.inputs);
    recalculate();
    incumbency.focus();
  });
  await selectRace(client, races[0].target_id);
}

start().catch((error) => {
  explorer.setAttribute("aria-busy", "false");
  explorer.innerHTML = `<section class="panel message message--error"><h2>Forecast explorer could not load</h2><p>${error instanceof Error ? error.message : String(error)}</p></section>`;
});
