// The published forecast the site is built from, and the target it locks.
// web/src/main.ts reads the same bundle name at runtime.
export const FORECAST = "14d-r2";
export const TARGET = "target_r2.csv";

// Ballot designation -> bundle party letter, matching PARTY_LETTERS in
// src/legmodel/interactive.py and PARTIES in web/src/presentation.ts.
export const PARTY_LETTERS = {
  Democratic: "D",
  Republican: "R",
  Unenrolled: "U",
  Independent: "I",
  "Workers Party": "WP",
  "Gulf War Veteran": "GWV",
};
