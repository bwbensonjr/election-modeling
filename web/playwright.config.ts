import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:4173/election-modeling/",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "GITHUB_ACTIONS=true npm run build && npm exec vite -- preview --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173/election-modeling/",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
