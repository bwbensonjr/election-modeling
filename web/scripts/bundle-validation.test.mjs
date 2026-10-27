import assert from "node:assert/strict";
import test from "node:test";
import { parseCsv, validateComparisonParties } from "./bundle-validation.mjs";

function fixture() {
  return {
    manifest: {
      races: [{
        target_id: "race-1",
        office: "State Representative",
        district: "First Example",
        dem_candidate: { name: "Alex Democrat", party: "D", municipality: "Example", is_incumbent: false },
        comparison_candidate: { name: "Riley Republican, Jr.", party: "R", municipality: "Example", is_incumbent: false },
      }],
    },
    targets: [{
      target_id: "race-1",
      office: "State Representative",
      district: "First Example",
      dem_candidate_name: "Alex Democrat",
      comparison_candidate_name: "Riley Republican, Jr.",
      comparison_candidate_party: "Republican",
      dem_candidate_municipality: "Example",
      dem_candidate_incumbent: "False",
      comparison_candidate_municipality: "Example",
      comparison_candidate_incumbent: "False",
    }],
  };
}

test("CSV parsing preserves quoted commas", () => {
  const rows = parseCsv("target_id,comparison_candidate_name,comparison_candidate_party\nrace-1,\"Riley Republican, Jr.\",Republican\n");
  assert.deepEqual(rows, [{
    target_id: "race-1",
    comparison_candidate_name: "Riley Republican, Jr.",
    comparison_candidate_party: "Republican",
  }]);
});

test("comparison-party validation accepts the locked invariant", () => {
  const { manifest, targets } = fixture();
  assert.doesNotThrow(() => validateComparisonParties(manifest, targets));
});

test("comparison-party validation rejects identity, metadata, and party mismatches", () => {
  const missing = fixture();
  missing.targets[0].target_id = "other";
  assert.throws(() => validateComparisonParties(missing.manifest, missing.targets), /missing from target/);

  const mismatched = fixture();
  mismatched.targets[0].district = "Second Example";
  assert.throws(() => validateComparisonParties(mismatched.manifest, mismatched.targets), /district disagrees/);

  const misletteredOpponent = fixture();
  misletteredOpponent.targets[0].comparison_candidate_party = "Unenrolled";
  assert.throws(
    () => validateComparisonParties(misletteredOpponent.manifest, misletteredOpponent.targets),
    /party disagrees/,
  );

  const unknownDesignation = fixture();
  unknownDesignation.targets[0].comparison_candidate_party = "Pirate";
  assert.throws(
    () => validateComparisonParties(unknownDesignation.manifest, unknownDesignation.targets),
    /Pirate has no party letter/,
  );

  const democraticOpponent = fixture();
  democraticOpponent.targets[0].comparison_candidate_party = "Democratic";
  assert.throws(
    () => validateComparisonParties(democraticOpponent.manifest, democraticOpponent.targets),
    /comparison candidate is a Democrat/,
  );
});

test("comparison-party validation accepts a non-Republican opponent with its designation letter", () => {
  const { manifest, targets } = fixture();
  targets[0].comparison_candidate_party = "Unenrolled";
  manifest.races[0].comparison_candidate.party = "U";
  assert.doesNotThrow(() => validateComparisonParties(manifest, targets));
});
