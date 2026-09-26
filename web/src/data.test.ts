import { createHash } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BundleClient, validateManifest } from "./data";
import type { Manifest } from "./types";

function manifest(): Manifest {
  return {
    schema_version: 1,
    election: "2026-11-03",
    horizon: "60d",
    variant: "forecast_60d",
    variant_declaration: "fixture",
    definition: "two_party_or_strongest",
    training_cutoff: "2024-11-05",
    finance_cutoff: "2026-09-04",
    source_code_commit: "abc",
    source_snapshot: "snapshot",
    source_snapshot_url: "https://example.com",
    source_digests: {},
    summary_tolerances: {
      point_margin: 1e-9,
      lower_90: 1e-9,
      upper_90: 1e-9,
      dem_win_probability: 1e-12,
    },
    draw_count: 3,
    components: {
      model: {
        asset: "components/model.json",
        predictors: ["PVI_N", "incumbent_status"],
        scenario_terms: ["incumbent_dem", "incumbent_gop"],
        numeric_support: {},
        categorical_support: {
          incumbent_status: {
            No_Incumbent: 1,
            Dem_Incumbent: 1,
            GOP_Incumbent: 1,
          },
        },
      },
    },
    races: [
      {
        target_id: "race",
        election_date: "2026-11-03",
        office: "State Representative",
        district: "First Example",
        district_display: "1st Example",
        dem_candidate_name: "A",
        comparison_candidate_name: "B",
        component: "model",
        asset: "races/race.json",
        published: {
          point_margin: 0,
          lower_90: -1,
          upper_90: 1,
          dem_win_probability: 1 / 3,
        },
        inputs: {
          PVI_N: 0,
          incumbent_status: "No_Incumbent",
          dem_receipts: null,
          opponent_receipts: null,
          money_predictor: null,
          money_logratio: null,
        },
        support: [],
      },
    ],
    assets: {},
  };
}

function digest(text: string): string {
  return `sha256:${createHash("sha256").update(text).digest("hex")}`;
}

afterEach(() => vi.unstubAllGlobals());

describe("bundle loading", () => {
  it("rejects unsupported schemas, duplicates, and absent components", () => {
    const unsupported = manifest();
    unsupported.schema_version = 2;
    expect(() => validateManifest(unsupported)).toThrow(/unsupported/);

    const duplicate = manifest();
    duplicate.races.push({ ...duplicate.races[0] });
    expect(() => validateManifest(duplicate)).toThrow(/duplicate/);

    const missing = manifest();
    missing.races[0].component = "absent";
    expect(() => validateManifest(missing)).toThrow(/missing component/);
  });

  it("verifies asset digests and draw lengths", async () => {
    const value = manifest();
    const raceText = JSON.stringify({ schema_version: 1, target_id: "race", draws: [-1, 0, 1] });
    value.assets["races/race.json"] = digest(raceText);
    const fetchMock = vi.fn(async () => new Response(raceText));
    vi.stubGlobal("fetch", fetchMock);
    const client = new BundleClient("/data", value);
    expect((await client.loadRace("race")).draws).toEqual([-1, 0, 1]);

    value.assets["races/race.json"] = "sha256:wrong";
    await expect(new BundleClient("/data", value).loadRace("race")).rejects.toThrow(/digest mismatch/);
  });
});
