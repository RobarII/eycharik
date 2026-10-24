import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end checks run against the demo API, so a laptop with no database can still prove that the
 * cabinet boots, logs in, pages, and takes a write.
 *
 * `vite --mode preview` serves the real bundle and a fixture `/admin/api` (see `preview/plugin.ts`).
 *
 * These specs assert against that fixture: exact names, exact counters, mutations that answer
 * synchronously. The same assertions against a real database would be a different test, so the run
 * through nginx, the API and Postgres lives in `playwright.stack.config.ts`.
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
  // Four viewports, because the shell has three shapes: a 248px sidebar, a 78px icon rail, and a
  // fixed bottom bar. Only running all three keeps the layout honest — every defect found in the
  // rail and in landscape was invisible to a desktop-only run. CI installs Chromium alone, so the
  // iPad project borrows it: the viewport and `pointer: coarse` are what the layout reacts to.
  //
  // Only layout and axe repeat per viewport. The cabinet flows mutate the in-memory demo (a claim, an
  // offboard, an edited document) and every project shares one server, so running them twice would
  // race on that state rather than test a second shape.
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "tablet",
      use: { ...devices["iPad Mini"], browserName: "chromium" },
      testMatch: /(layout|a11y)\.spec\.ts/,
    },
    { name: "phone", use: { ...devices["Pixel 7"] }, testMatch: /(layout|a11y)\.spec\.ts/ },
    {
      name: "phone-landscape",
      use: { ...devices["Pixel 7 landscape"] },
      testMatch: /(layout|a11y)\.spec\.ts/,
    },
  ],
  webServer: {
    command: "npm run preview:demo -- --port 5199 --strictPort",
    url: "http://127.0.0.1:5199",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
