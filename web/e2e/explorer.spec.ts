import AxeBuilder from "@axe-core/playwright";
import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";

test("explores every published race and resets a changed scenario", async ({ page }) => {
  await page.goto("./");
  await expect(page.locator("#explorer")).toHaveAttribute("aria-busy", "false");
  await expect(page.locator("#race-select option")).toHaveCount(46);
  await expect(page.locator(".density-line")).toHaveCount(2);
  await expect(page.locator("#scenario-status")).toHaveText("Matches published");

  const original = await page.locator("#scenario-summary").textContent();
  const currentIncumbency = await page.locator("#incumbency").inputValue();
  const changedIncumbency = currentIncumbency === "Dem_Incumbent" ? "No_Incumbent" : "Dem_Incumbent";
  await page.locator("#incumbency").selectOption(changedIncumbency);
  await expect(page.locator("#scenario-status")).toHaveText("Hypothetical");
  await expect(page.locator("#scenario-summary")).not.toHaveText(original || "");

  await page.locator("#dem-receipts").fill("1000000000000000");
  await page.locator("#opponent-receipts").fill("0");
  await expect(page.locator("#scenario-status")).toHaveText("Hypothetical");
  await expect(page.locator("#support-warning")).toContainText("outside the historical range");
  await expect(page.locator(".methodology")).toContainText("does not show the causal effect");
  await expect(page.locator("#incumbency-support")).toContainText("training races");
  await page.locator("#reset").click();
  await expect(page.locator("#scenario-status")).toHaveText("Matches published");
  await expect(page.locator("#incumbency")).toBeFocused();

  const secondTarget = await page.locator("#race-select option").nth(1).getAttribute("value");
  await page.locator("#race-select").selectOption(secondTarget || "");
  await expect(page.locator("#scenario-status")).toHaveText("Matches published");
});

test("production base path, narrow layout, keyboard controls, and accessibility work", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("./");
  await expect(page.locator("#explorer")).toHaveAttribute("aria-busy", "false");
  expect(page.url()).toContain("/election-modeling/");
  const panel = await page.locator(".race-picker").boundingBox();
  expect(panel?.width).toBeLessThanOrEqual(382);

  await page.locator("body").press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await page.locator(".skip-link").press("Enter");
  await expect(page.locator("#explorer")).toBeFocused();

  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("a fallback component disables fundraising without rerouting", async ({ page }) => {
  const raceAsset = JSON.stringify({ schema_version: 1, target_id: "fallback", draws: [-1, 0, 1] }) + "\n";
  const componentAsset = JSON.stringify({
    schema_version: 1,
    component: "baseline_no_timing",
    predictors: ["PVI_N", "incumbent_status"],
    terms: { incumbent_dem: [2, 2, 2], incumbent_gop: [-2, -2, -2] },
    numeric_support: { incumbent_dem: { minimum: 0, maximum: 1 }, incumbent_gop: { minimum: 0, maximum: 1 } },
    categorical_support: { incumbent_status: { No_Incumbent: 10, Dem_Incumbent: 20, GOP_Incumbent: 5 } },
  }) + "\n";
  const digest = (value: string) => `sha256:${createHash("sha256").update(value).digest("hex")}`;
  const manifest = {
    schema_version: 1,
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
    draw_count: 3,
    components: {
      baseline_no_timing: {
        asset: "components/baseline_no_timing.json",
        predictors: ["PVI_N", "incumbent_status"],
        scenario_terms: ["incumbent_dem", "incumbent_gop"],
        numeric_support: {},
        categorical_support: { incumbent_status: { No_Incumbent: 10, Dem_Incumbent: 20, GOP_Incumbent: 5 } },
      },
    },
    races: [{
      target_id: "fallback",
      election_date: "2026-11-03",
      office: "State Representative",
      district: "Example",
      district_display: "Example",
      dem_candidate_name: "Dem Candidate",
      comparison_candidate_name: "Other Candidate",
      component: "baseline_no_timing",
      asset: "races/fallback.json",
      published: { point_margin: 0, lower_90: -0.9, upper_90: 0.9, dem_win_probability: 1 / 3 },
      inputs: { PVI_N: 0, incumbent_status: "No_Incumbent", dem_receipts: null, opponent_receipts: null, money_predictor: null, money_logratio: null },
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
  await page.goto("./");
  await expect(page.locator("#dem-receipts")).toBeDisabled();
  await expect(page.locator("#opponent-receipts")).toBeDisabled();
  await expect(page.locator("#finance-note")).toContainText("no-finance fallback");
  await page.locator("#incumbency").selectOption("GOP_Incumbent");
  await expect(page.locator("#scenario-status")).toHaveText("Hypothetical");
});
