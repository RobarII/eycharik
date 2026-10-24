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
  { name: "run detail", hash: "#/run/9c8b7a65-4321-4f0e-9d8c-7b6a5f4e3d2c" },
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
