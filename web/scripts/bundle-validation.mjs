export function parseCsv(text) {
  const records = [];
  let record = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === "\"") {
      if (quoted && text[index + 1] === "\"") {
        field += "\"";
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      record.push(field);
      field = "";
    } else if (character === "\n" && !quoted) {
      record.push(field);
      records.push(record);
      record = [];
      field = "";
    } else if (character !== "\r" || quoted) {
      field += character;
    }
  }
  if (quoted) throw new Error("target CSV has an unterminated quoted field");
  if (field || record.length) {
    record.push(field);
    records.push(record);
  }
  const [headers, ...rows] = records;
  if (!headers?.length) throw new Error("target CSV is empty");
  return rows
    .filter((row) => row.some((value) => value !== ""))
    .map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])));
}

export function validateComparisonParties(manifest, targetRows) {
  const targets = new Map();
  for (const row of targetRows) {
    if (!row.target_id || targets.has(row.target_id)) {
      throw new Error(`target data has a missing or duplicate identity: ${row.target_id || "<missing>"}`);
    }
    targets.set(row.target_id, row);
  }
  if (targets.size !== manifest.races.length) {
    throw new Error(`bundle and target race counts disagree: ${manifest.races.length} versus ${targets.size}`);
  }
  for (const race of manifest.races) {
    const target = targets.get(race.target_id);
    if (!target) throw new Error(`${race.target_id}: bundle race is missing from target data`);
    for (const field of ["office", "district", "dem_candidate_name", "comparison_candidate_name"]) {
      if (String(race[field]) !== String(target[field])) {
        throw new Error(`${race.target_id}: bundle ${field} disagrees with target data`);
      }
    }
    if (target.comparison_candidate_party !== "Republican") {
      throw new Error(`${race.target_id}: comparison candidate is ${target.comparison_candidate_party || "missing"}, not Republican`);
    }
  }
  const manifestIds = new Set(manifest.races.map((race) => race.target_id));
  const extra = [...targets.keys()].find((targetId) => !manifestIds.has(targetId));
  if (extra) throw new Error(`${extra}: target race is missing from the interactive bundle`);
}
