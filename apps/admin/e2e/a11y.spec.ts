import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { HR, signedInAs } from "./session";

/**
 * Axe on the screens a recruiter actually uses.
 *
 * Only `critical` and `serious` fail the build: `moderate` findings here are mostly cosmetic and a
 * noisy rule is a rule people learn to ignore.
 */
const SCREENS: ReadonlyArray<{ name: string; hash: string }> = [
  { name: "overview", hash: "#/overview" },
  { name: "runs", hash: "#/runs" },
  { name: "questions", hash: "#/questions" },
  { name: "risk", hash: "#/risk" },
  { name: "knowledge", hash: "#/knowledge" },
  { name: "run detail", hash: "#/run/4a1d2c3b-5e6f-4a71-8b92-0c1d2e3f4a5b" },
  { name: "not found", hash: "#/nonsense" },
];

test("the gate is accessible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByLabel("Токен доступа")).toBeVisible();

  const { violations } = await new AxeBuilder({ page }).analyze();
  expect(violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""))).toEqual([]);
});

for (const screen of SCREENS) {
  test(`the ${screen.name} screen is accessible`, async ({ page }) => {
    await signedInAs(page, HR);
    await page.goto(`/${screen.hash}`);
    // The screens poll, so "network idle" never settles; wait for the heading and let the first
    // render finish instead.
    await page.getByRole("heading", { level: 1 }).first().waitFor();
    await page.waitForTimeout(600);

    const { violations } = await new AxeBuilder({ page }).analyze();
    expect(violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""))).toEqual([]);
  });
}
