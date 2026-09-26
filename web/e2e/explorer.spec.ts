import AxeBuilder from "@axe-core/playwright";
import { createHash } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";

const digest = (value: string) => `sha256:${createHash("sha256").update(value).digest("hex")}`;

async function installFixture(page: Page, options: { draws: number[]; probability: number; finance?: boolean }): Promise<void> {
  const finance = options.finance ?? false;
  const targetId = "fallback";
  const raceAsset = JSON.stringify({ schema_version: 2, target_id: targetId, draws: options.draws }) + "\n";
  const componentAsset = JSON.stringify({
    schema_version: 2,
    component: "baseline_no_timing",
    predictors: finance ? ["PVI_N", "incumbent_status", "money_logratio_wide"] : ["PVI_N", "incumbent_status"],
    terms: {
      incumbent_dem: options.draws.map(() => 2),
      incumbent_gop: options.draws.map(() => -2),
      ...(finance ? { money_logratio_wide: options.draws.map(() => 0.5) } : {}),
    },
    numeric_support: finance ? { money_logratio_wide: { minimum: -2, maximum: 2 } } : {},
    categorical_support: { incumbent_status: { No_Incumbent: 10, Dem_Incumbent: 20, GOP_Incumbent: 5 } },
  }) + "\n";
  const manifest = {
    schema_version: 2,
    election: "2026-11-03",
    horizon: "60d",
    variant: "forecast_60d",
    variant_declaration: "fixture",
    definition: "two_party_or_strongest",
    training_cutoff: "2024-11-05",
    finance_cutoff: "2026-09-04",
    source_code_commit: "abc123456789",
    source_snapshot: "fixture",
    source_snapshot_url: "https://example.com",
    source_digests: {},
    summary_tolerances: { point_margin: 1e-9, lower_90: 1e-9, upper_90: 1e-9, dem_win_probability: 1e-12 },
    draw_count: options.draws.length,
    components: {
      baseline_no_timing: {
        asset: "components/baseline_no_timing.json",
        predictors: finance ? ["PVI_N", "incumbent_status", "money_logratio_wide"] : ["PVI_N", "incumbent_status"],
        scenario_terms: finance ? ["incumbent_dem", "incumbent_gop", "money_logratio_wide"] : ["incumbent_dem", "incumbent_gop"],
        numeric_support: finance ? { money_logratio_wide: { minimum: -2, maximum: 2 } } : {},
        categorical_support: { incumbent_status: { No_Incumbent: 10, Dem_Incumbent: 20, GOP_Incumbent: 5 } },
      },
    },
    races: [{
      target_id: targetId,
      election_date: "2026-11-03",
      office: "State Representative",
      district: "Example",
      district_display: "Example",
      dem_candidate: { name: "Margaret R. Scarsdale", party: "D", municipality: "Pepperell", is_incumbent: true },
      comparison_candidate: { name: "Republican Candidate", party: "R", municipality: "Example", is_incumbent: false },
      component: "baseline_no_timing",
      asset: "races/fallback.json",
      published: {
        point_margin: options.draws.reduce((sum, value) => sum + value, 0) / options.draws.length,
        lower_90: Math.min(...options.draws),
        upper_90: Math.max(...options.draws),
        dem_win_probability: options.probability,
      },
      inputs: {
        PVI_N: 0.4,
        incumbent_status: "No_Incumbent",
        dem_receipts: finance ? 1000.4 : null,
        opponent_receipts: finance ? 999.6 : null,
        money_predictor: finance ? "money_logratio_wide" : null,
        money_logratio: finance ? Math.log(1001.4 / 1000.6) : null,
      },
      support: [],
    }],
    assets: {
      "races/fallback.json": digest(raceAsset),
      "components/baseline_no_timing.json": digest(componentAsset),
    },
  };

  await page.route("**/data/2026/60d/manifest.json", (route) => route.fulfill({ json: manifest }));
  await page.route("**/data/2026/60d/races/fallback.json", (route) => route.fulfill({ body: raceAsset, contentType: "application/json" }));
  await page.route("**/data/2026/60d/components/baseline_no_timing.json", (route) => route.fulfill({ body: componentAsset, contentType: "application/json" }));
}

test("overview contains every race in competitiveness order without eager asset loads", async ({ page }) => {
  const assetRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/data\/2026\/60d\/(races|components)\//.test(request.url())) assetRequests.push(request.url());
  });
  await page.goto("./");
  await expect(page.locator("#overview-view")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("#race-overview-body tr")).toHaveCount(46);
  await expect(page.locator("#race-overview thead th")).toHaveCount(5);
  expect(assetRequests).toEqual([]);

  const margins = await page.locator("#race-overview-body tr").evaluateAll((rows) =>
    rows.map((row) => Number((row as HTMLElement).dataset.absoluteMargin)),
  );
  expect(margins).toEqual([...margins].sort((left, right) => left - right));
  await expect(page.locator("#race-overview-body tr").first()).toContainText(/Democratic|Republican|Toss-up/);
  await expect(page.locator("#race-overview-body tr").first()).toContainText(/\d+%/);
});

test("race links support pointer, keyboard, history, direct refresh, and invalid URLs", async ({ page }) => {
  await page.goto("./");
  const firstLink = page.locator(".race-link").first();
  const firstTarget = await firstLink.evaluate((link) => new URL((link as HTMLAnchorElement).href).searchParams.get("race"));
  await firstLink.click();
  await expect(page.locator("#explorer")).toHaveAttribute("aria-busy", "false");
  expect(new URL(page.url()).searchParams.get("race")).toBe(firstTarget);
  await expect(page.locator(".density-line")).toHaveCount(2);

  await page.goBack();
  await expect(page.locator("#overview-view")).toBeVisible();
  await page.locator(".race-link").nth(1).focus();
  await page.locator(".race-link").nth(1).press("Enter");
  await expect(page.locator("#explorer")).toHaveAttribute("aria-busy", "false");
  const directUrl = page.url();
  await page.reload();
  await expect(page.locator("#explorer")).toHaveAttribute("aria-busy", "false");
  expect(page.url()).toBe(directUrl);
  await page.locator("#overview-link").click();
  await expect(page.locator("#overview-view")).toBeVisible();
  await page.goBack();
  await expect(page.locator("#explorer")).toBeVisible();
  await page.goForward();
  await expect(page.locator("#overview-view")).toBeVisible();

  await page.goto("./?race=not-a-published-race");
  await expect(page.locator("#overview-view")).toBeVisible();
  await expect(page.locator("#route-error")).toContainText("No published race matches");
  await expect(page.locator("#race-overview-body tr")).toHaveCount(46);
});

test("matchup uses whole numbers, grouped receipts, exact reset state, and accessible layouts", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");
  await page.locator(".race-link").first().click();
  await expect(page.locator("#explorer")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("#published-summary")).not.toContainText(/\d+\.\d/);
  await expect(page.locator("#published-inputs")).not.toContainText(/\d+\.\d/);
  await expect(page.locator("#race-context")).toContainText(/\*? \([DR]-[^)]+\)/);
  await expect(page.locator("#race-context")).toContainText("An asterisk (*) marks an incumbent candidate.");
  await expect(page.locator("#published-summary")).toContainText("Likely Margin");
  await expect(page.locator("#published-inputs")).toContainText(/(?:D|R)\+\d+|Even/);
  await expect(page.locator("#dem-receipts")).toHaveValue(/^\d{1,3}(,\d{3})+$/);
  await expect(page.locator("#opponent-receipts")).toHaveValue(/^\d{1,3}(,\d{3})+$/);

  const publishedReceipts = await page.locator("#dem-receipts").inputValue();
  const currentIncumbency = await page.locator("#incumbency").inputValue();
  const changedIncumbency = currentIncumbency === "Dem_Incumbent" ? "No_Incumbent" : "Dem_Incumbent";
  await page.locator("#incumbency").selectOption(changedIncumbency);
  await expect(page.locator("#scenario-status")).toHaveText("Hypothetical");
  await expect(page.locator("#dem-receipts")).toHaveValue(publishedReceipts);

  await page.locator("#dem-receipts").fill("1,000,000");
  await page.locator("#dem-receipts").blur();
  await expect(page.locator("#dem-receipts")).toHaveValue("1,000,000");
  await page.locator("#dem-receipts").fill("1.5");
  await expect(page.locator("#input-error")).toContainText("whole dollars");
  await page.locator("#reset").click();
  await expect(page.locator("#scenario-status")).toHaveText("Matches published");
  await expect(page.locator("#dem-receipts")).toHaveValue(publishedReceipts);
  await expect(page.locator("#incumbency")).toBeFocused();

  const panel = await page.locator(".race-picker").boundingBox();
  expect(panel?.width).toBeLessThanOrEqual(382);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("favored-party summaries handle Republican, Democratic, toss-up, and fallback states", async ({ page }) => {
  await installFixture(page, { draws: [-1, 0, 1], probability: 1 / 3 });
  await page.goto("./?race=fallback");
  await expect(page.locator("#published-summary")).toContainText("Republican win");
  await expect(page.locator("#published-summary")).toContainText("67%");
  await expect(page.locator("#dem-receipts")).toBeDisabled();
  await expect(page.locator("#opponent-receipts")).toBeDisabled();
  await expect(page.locator("#finance-note")).toContainText("no-finance fallback");
  await page.locator("#incumbency").selectOption("Dem_Incumbent");
  await expect(page.locator("#scenario-summary")).toContainText("Democratic win");
  await expect(page.locator("#scenario-summary")).toContainText("Favorite changes: Republican to Democratic");
});

test("an exact even probability is displayed as a toss-up", async ({ page }) => {
  await installFixture(page, { draws: [-1, 1], probability: 0.5 });
  await page.goto("./?race=fallback");
  await expect(page.locator("#published-summary")).toContainText("Toss-up");
  await expect(page.locator("#published-summary")).toContainText("50%");
});

test("overview is keyboard accessible at the production base path", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");
  expect(page.url()).toContain("/election-modeling/");
  await page.locator("body").press("Tab");
  await expect(page.locator("#skip-link")).toBeFocused();
  await page.locator("#skip-link").press("Enter");
  await expect(page.locator("#overview-view")).toBeFocused();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
