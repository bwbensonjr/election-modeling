import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { parseCsv, validateComparisonParties } from "./bundle-validation.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../data/forecast/2026/interactive/60d");
const manifest = JSON.parse(await readFile(path.join(root, "manifest.json"), "utf8"));
const targetRows = parseCsv(await readFile(path.resolve(here, "../../data/forecast/2026/target.csv"), "utf8"));

if (manifest.schema_version !== 2) {
  throw new Error(`unsupported bundle schema ${manifest.schema_version}`);
}
if (manifest.races.length === 0 || new Set(manifest.races.map((race) => race.target_id)).size !== manifest.races.length) {
  throw new Error("bundle races are empty or duplicated");
}
for (const [asset, expected] of Object.entries(manifest.assets)) {
  const bytes = await readFile(path.join(root, asset));
  const actual = `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
  if (actual !== expected) {
    throw new Error(`${asset}: expected ${expected}, got ${actual}`);
  }
}
for (const race of manifest.races) {
  if (!manifest.components[race.component]) {
    throw new Error(`${race.target_id}: missing component ${race.component}`);
  }
}
validateComparisonParties(manifest, targetRows);
console.log(`validated ${manifest.races.length} races and ${Object.keys(manifest.assets).length} assets`);
