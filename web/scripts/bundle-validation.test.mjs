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
        dem_candidate_name: "Alex Democrat",
        comparison_candidate_name: "Riley Republican, Jr.",
      }],
    },
    targets: [{
      target_id: "race-1",
      office: "State Representative",
      district: "First Example",
      dem_candidate_name: "Alex Democrat",
      comparison_candidate_name: "Riley Republican, Jr.",
      comparison_candidate_party: "Republican",
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

  const nonRepublican = fixture();
  nonRepublican.targets[0].comparison_candidate_party = "Unenrolled";
  assert.throws(() => validateComparisonParties(nonRepublican.manifest, nonRepublican.targets), /not Republican/);
});
