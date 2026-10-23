import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end checks run against the demo API, so a laptop with no database can still prove that the
 * cabinet boots, logs in, pages, and takes a write.
 *
 * `vite --mode preview` serves the real bundle and a fixture `/admin/api` (see `preview/plugin.ts`).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5199",
    // The cabinet honours `prefers-reduced-motion`; emulating it also makes screenshots and axe
    // scans deterministic instead of catching a card mid-fade.
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run preview:demo -- --port 5199 --strictPort",
    url: "http://127.0.0.1:5199",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
