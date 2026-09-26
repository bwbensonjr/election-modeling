import "./style.css";
import { renderDistribution } from "./chart";
import { BundleClient } from "./data";
import {
  formatDollarInput,
  formatDollars,
  formatInterval,
  formatCandidate,
  formatMargin,
  formatPercent,
  formatPvi,
  formatSignedInteger,
  likelyWinner,
  parseDollarInput,
  probabilityComparison,
  racesByCompetitiveness,
} from "./presentation";
import {
  initialScenario,
  outsideSupport,
  receiptLogRatio,
  scenarioDraws,
  summarize,
  withScenarioIncumbency,
  withScenarioReceipt,
} from "./scenario";
import type { ComponentAsset, Incumbency, RaceAsset, RaceMeta, ScenarioInputs, Summary } from "./types";

function required<T extends Element>(selector: string): T {
  const value = document.querySelector<T>(selector);
  if (!value) throw new Error(`missing application element ${selector}`);
  return value;
}

const overview = required<HTMLElement>("#overview-view");
const explorer = required<HTMLElement>("#explorer");
const skipLink = required<HTMLAnchorElement>("#skip-link");
const overviewLink = required<HTMLAnchorElement>("#overview-link");
const routeError = required<HTMLElement>("#route-error");
const raceOverviewBody = required<HTMLTableSectionElement>("#race-overview-body");
const overviewCaption = required<HTMLTableCaptionElement>("#overview-caption");
const raceSelect = required<HTMLSelectElement>("#race-select");
const incumbency = required<HTMLSelectElement>("#incumbency");
const demReceipts = required<HTMLInputElement>("#dem-receipts");
const opponentReceipts = required<HTMLInputElement>("#opponent-receipts");
const reset = required<HTMLButtonElement>("#reset");
const inputError = required<HTMLElement>("#input-error");
const supportWarning = required<HTMLElement>("#support-warning");
const scenarioStatus = required<HTMLElement>("#scenario-status");

let currentRace: RaceMeta;
let currentRaceAsset: RaceAsset;
let currentComponent: ComponentAsset;
let currentScenario: ScenarioInputs;
let loadSequence = 0;
let receiptValidity = { dem_receipts: true, opponent_receipts: true };

function summaryMarkup(summary: Summary, comparison?: Summary): string {
  const winner = likelyWinner(summary.dem_win_probability);
  const winnerLabel = winner.party === "Toss-up" ? "Toss-up" : `${winner.party} win`;
  const marginDelta = comparison
    ? formatSignedInteger(summary.point_margin - comparison.point_margin, " pts")
    : "";
  const probabilityDelta = comparison
    ? probabilityComparison(summary.dem_win_probability, comparison.dem_win_probability)
    : "";
  return `
    <div class="stat"><span class="stat__label">Likely Margin</span><strong>${formatMargin(summary.point_margin)}</strong>${comparison ? `<small>${marginDelta}</small>` : ""}</div>
    <div class="stat"><span class="stat__label">90% interval</span><strong>${formatInterval(summary.lower_90, summary.upper_90)}</strong></div>
    <div class="stat"><span class="stat__label">${winnerLabel}</span><strong>${formatPercent(winner.probability)}</strong>${comparison ? `<small>${probabilityDelta}</small>` : ""}</div>
  `;
}

function isChanged(): boolean {
  const original = currentRace.inputs;
  return currentScenario.incumbent_status !== original.incumbent_status
    || currentScenario.dem_receipts !== original.dem_receipts
    || currentScenario.opponent_receipts !== original.opponent_receipts;
}

function showInputError(error: unknown): void {
  inputError.textContent = error instanceof Error ? error.message : String(error);
  inputError.hidden = false;
}

function recalculate(): void {
  try {
    const draws = scenarioDraws(currentRaceAsset.draws, currentRace.inputs, currentScenario, currentComponent);
    const scenarioSummary = summarize(draws);
    const changed = isChanged();
    required<HTMLElement>("#scenario-summary").innerHTML = summaryMarkup(
      scenarioSummary,
      changed ? currentRace.published : undefined,
    );
    scenarioStatus.textContent = changed ? "Hypothetical" : "Matches published";
    scenarioStatus.classList.toggle("status-pill--changed", changed);
    if (receiptValidity.dem_receipts && receiptValidity.opponent_receipts) inputError.hidden = true;

    let warning: string | null = null;
    if (currentRace.inputs.money_predictor && currentScenario.dem_receipts !== null && currentScenario.opponent_receipts !== null) {
      const value = receiptLogRatio(currentScenario.dem_receipts, currentScenario.opponent_receipts);
      warning = outsideSupport(value, currentComponent.numeric_support[currentRace.inputs.money_predictor]);
    }
    supportWarning.hidden = warning === null;
    supportWarning.textContent = warning || "";
    renderDistribution(required<HTMLElement>("#chart"), currentRaceAsset.draws, draws);
  } catch (error) {
    showInputError(error);
  }
}

function renderRaceContext(race: RaceMeta): void {
  required<HTMLElement>("#race-context").innerHTML = `
    <p class="matchup"><strong>${formatCandidate(race.dem_candidate)}</strong><span>vs.</span><strong>${formatCandidate(race.comparison_candidate)}</strong></p>
    <p class="field-note">An asterisk (*) marks an incumbent candidate.</p>
    <p>${race.office} · ${race.district_display}</p>
  `;
  required<HTMLElement>("#published-summary").innerHTML = summaryMarkup(race.published);
  required<HTMLElement>("#published-inputs").innerHTML = `
    <div><dt>District PVI</dt><dd>${formatPvi(race.inputs.PVI_N)}</dd></div>
    <div><dt>Incumbency</dt><dd>${race.inputs.incumbent_status.replaceAll("_", " ")}</dd></div>
    <div><dt>Democratic receipts</dt><dd>${race.inputs.dem_receipts === null ? "Not used" : formatDollars(race.inputs.dem_receipts)}</dd></div>
    <div><dt>Republican receipts</dt><dd>${race.inputs.opponent_receipts === null ? "Not used" : formatDollars(race.inputs.opponent_receipts)}</dd></div>
  `;
}

function setReceiptControls(race: RaceMeta): void {
  const hasFinance = race.inputs.money_predictor !== null;
  demReceipts.disabled = !hasFinance;
  opponentReceipts.disabled = !hasFinance;
  demReceipts.value = race.inputs.dem_receipts === null ? "" : formatDollarInput(race.inputs.dem_receipts);
  opponentReceipts.value = race.inputs.opponent_receipts === null ? "" : formatDollarInput(race.inputs.opponent_receipts);
  receiptValidity = { dem_receipts: true, opponent_receipts: true };
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
  raceSelect.value = race.target_id;
  renderRaceContext(race);
  incumbency.value = race.inputs.incumbent_status;
  setReceiptControls(race);
  const hasFinance = race.inputs.money_predictor !== null;
  required<HTMLElement>("#finance-note").textContent = hasFinance
    ? `Receipts are displayed as whole dollars and measured at the ${manifest.horizon} cutoff (${manifest.finance_cutoff}). The model uses their full-precision log ratio until you edit an amount.`
    : "Fundraising controls are unavailable because this race uses the no-finance fallback component; scenarios do not switch components.";
  const counts = component.categorical_support.incumbent_status;
  required<HTMLElement>("#incumbency-support").textContent = `${counts[race.inputs.incumbent_status]} training races used the published incumbency level.`;
  inputError.hidden = true;
  recalculate();
  explorer.setAttribute("aria-busy", "false");
}

function applicationUrl(): URL {
  return new URL(import.meta.env.BASE_URL, window.location.origin);
}

function raceUrl(targetId: string): string {
  const url = applicationUrl();
  url.searchParams.set("race", targetId);
  return `${url.pathname}${url.search}`;
}

function updateHistory(targetId: string | null): void {
  const url = applicationUrl();
  if (targetId) url.searchParams.set("race", targetId);
  window.history.pushState({}, "", `${url.pathname}${url.search}`);
}

function showOverview(error?: string): void {
  loadSequence += 1;
  explorer.hidden = true;
  overview.hidden = false;
  overview.setAttribute("aria-busy", "false");
  skipLink.href = "#overview-view";
  routeError.hidden = !error;
  routeError.textContent = error || "";
}

async function showMatchup(client: BundleClient, targetId: string): Promise<void> {
  routeError.hidden = true;
  overview.hidden = true;
  explorer.hidden = false;
  skipLink.href = "#explorer";
  await selectRace(client, targetId);
}

async function renderRoute(client: BundleClient): Promise<void> {
  const targetId = new URL(window.location.href).searchParams.get("race");
  if (!targetId) {
    showOverview();
    return;
  }
  const race = client.getManifest().races.find((candidate) => candidate.target_id === targetId);
  if (!race) {
    showOverview(`No published race matches “${targetId}”. Choose a race from the complete overview.`);
    return;
  }
  await showMatchup(client, targetId);
}

function navigate(client: BundleClient, targetId: string | null): void {
  updateHistory(targetId);
  void renderRoute(client).catch(renderFatalError);
}

function renderOverview(races: RaceMeta[], client: BundleClient): void {
  const ordered = racesByCompetitiveness(races);
  overviewCaption.textContent = `Published forecasts for all ${ordered.length} races in the locked snapshot`;
  raceOverviewBody.replaceChildren(...ordered.map((race) => {
    const winner = likelyWinner(race.published.dem_win_probability);
    const row = document.createElement("tr");
    row.dataset.targetId = race.target_id;
    row.dataset.absoluteMargin = String(Math.abs(race.published.point_margin));

    const raceCell = document.createElement("td");
    const link = document.createElement("a");
    link.className = "race-link";
    link.href = raceUrl(race.target_id);
    link.textContent = race.district_display;
    link.addEventListener("click", (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      navigate(client, race.target_id);
    });
    const office = document.createElement("span");
    office.className = "race-office";
    office.textContent = race.office.replace("State ", "");
    raceCell.append(link, office);

    const matchup = document.createElement("td");
    matchup.className = "race-matchup";
    matchup.textContent = `${formatCandidate(race.dem_candidate)} vs. ${formatCandidate(race.comparison_candidate)}`;
    const party = document.createElement("td");
    party.textContent = winner.party;
    const chance = document.createElement("td");
    chance.textContent = formatPercent(winner.probability);
    const margin = document.createElement("td");
    margin.textContent = formatMargin(race.published.point_margin);
    row.append(raceCell, matchup, party, chance, margin);
    return row;
  }));
}

type ReceiptKey = "dem_receipts" | "opponent_receipts";

function updateReceipt(key: ReceiptKey, input: HTMLInputElement): void {
  try {
    const value = parseDollarInput(input.value);
    currentScenario = withScenarioReceipt(currentScenario, key, value);
    receiptValidity[key] = true;
    recalculate();
  } catch (error) {
    receiptValidity[key] = false;
    showInputError(error);
  }
}

function normalizeReceipt(key: ReceiptKey, input: HTMLInputElement): void {
  if (!receiptValidity[key]) return;
  const value = currentScenario[key];
  if (value !== null) input.value = formatDollarInput(value);
}

function renderFatalError(error: unknown): void {
  overview.setAttribute("aria-busy", "false");
  explorer.setAttribute("aria-busy", "false");
  const active = overview.hidden ? explorer : overview;
  active.innerHTML = `<section class="panel message message--error"><h2>Forecast explorer could not load</h2><p>${error instanceof Error ? error.message : String(error)}</p></section>`;
}

async function start(): Promise<void> {
  const baseUrl = `${import.meta.env.BASE_URL}data/2026/60d`.replace(/\/$/, "");
  const client = await BundleClient.load(baseUrl);
  const manifest = client.getManifest();
  const selectorRaces = [...manifest.races].sort((left, right) =>
    left.office.localeCompare(right.office)
    || left.district_display.localeCompare(right.district_display, undefined, { numeric: true }),
  );
  raceSelect.replaceChildren(...selectorRaces.map((race) => {
    const option = document.createElement("option");
    option.value = race.target_id;
    option.textContent = `${race.office.replace("State ", "")} — ${race.district_display}`;
    return option;
  }));
  renderOverview(manifest.races, client);
  overviewLink.href = applicationUrl().pathname;
  overviewLink.addEventListener("click", (event) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(client, null);
  });
  required<HTMLAnchorElement>("#snapshot-link").href = manifest.source_snapshot_url;
  required<HTMLElement>("#provenance").innerHTML = `
    <div><dt>Forecast horizon</dt><dd>${manifest.horizon} · cutoff ${manifest.finance_cutoff}</dd></div>
    <div><dt>Training cutoff</dt><dd>${manifest.training_cutoff}</dd></div>
    <div><dt>Model</dt><dd><code>${manifest.variant}</code></dd></div>
    <div><dt>Definition</dt><dd><code>${manifest.definition}</code></dd></div>
    <div><dt>Source revision</dt><dd><code>${manifest.source_code_commit.slice(0, 12)}</code></dd></div>
  `;

  raceSelect.addEventListener("change", () => navigate(client, raceSelect.value));
  incumbency.addEventListener("change", () => {
    currentScenario = withScenarioIncumbency(currentScenario, incumbency.value as Incumbency);
    const counts = currentComponent.categorical_support.incumbent_status;
    required<HTMLElement>("#incumbency-support").textContent = `${counts[incumbency.value as Incumbency]} training races used this incumbency level.`;
    recalculate();
  });
  demReceipts.addEventListener("input", () => updateReceipt("dem_receipts", demReceipts));
  opponentReceipts.addEventListener("input", () => updateReceipt("opponent_receipts", opponentReceipts));
  demReceipts.addEventListener("blur", () => normalizeReceipt("dem_receipts", demReceipts));
  opponentReceipts.addEventListener("blur", () => normalizeReceipt("opponent_receipts", opponentReceipts));
  reset.addEventListener("click", () => {
    incumbency.value = currentRace.inputs.incumbent_status;
    currentScenario = initialScenario(currentRace.inputs);
    setReceiptControls(currentRace);
    recalculate();
    incumbency.focus();
  });
  window.addEventListener("popstate", () => void renderRoute(client).catch(renderFatalError));
  await renderRoute(client);
}

start().catch(renderFatalError);
