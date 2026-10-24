import { defineConfig, devices } from "@playwright/test";

/**
 * The cabinet against the real stack: nginx serves the bundle, proxies `/admin/api` to the API, the
 * API talks to Postgres. Nothing is stubbed, and no server is started here — the caller brings the
 * compose stack up (`scripts/verify_demo.sh`) and this suite only reads from it.
 *
 * It is a separate project from `playwright.config.ts` on purpose. Those specs assert exact demo
 * counters and mutate the data; these assert that the wiring works and that every section renders
 * without a console error, which is what a fixture can never prove.
 */
export default defineConfig({
  testDir: "./e2e-stack",
  // One shared stack, and a failure is easier to read in a fixed order.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000",
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"] } }],
});
