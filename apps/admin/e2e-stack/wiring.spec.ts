import { expect, test } from "@playwright/test";

import { HR, nav, signedInAs } from "../e2e/session";

/**
 * What only a real stack can prove: the browser reaches the API through the cabinet's nginx, the
 * session cookie survives that hop, and every section renders against a real database.
 *
 * Read-only by design. The fixture suite owns the writes, because a write here lands in the demo
 * data that `scripts/verify_demo.sh` is checking at the same time.
 */

/** Sections the shell offers, with the heading each one must render. */
const SECTIONS: ReadonlyArray<{ label: string; heading: string }> = [
  { label: "Обзор", heading: "Обзор онбординга" },
  { label: "Сотрудники", heading: "Новые сотрудники" },
  { label: "Вопросы", heading: "Вопросы сотрудников" },
  { label: "Риски", heading: "Риски адаптации" },
  { label: "Знания", heading: "База знаний" },
];

test("the api answers through the cabinet's nginx", async ({ page }) => {
  await signedInAs(page, HR);

  const response = await page.evaluate(async () => {
    const api = await fetch("/admin/api/v1/me", { credentials: "same-origin" });
    const version = await fetch("/version.json", { cache: "no-store" });
    return {
      status: api.status,
      identity: (await api.json()) as { role?: string },
      versionStatus: version.status,
      build: ((await version.json()) as { build?: string }).build,
    };
  });

  expect(response.status).toBe(200);
  expect(response.identity.role).toBeTruthy();
  // The bundle was built from this commit and nginx serves it without caching.
  expect(response.versionStatus).toBe(200);
  expect(response.build).toBeTruthy();
});

test("every section renders against the real database", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("response", (response) => {
    if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`);
  });

  await signedInAs(page, HR);

  for (const section of SECTIONS) {
    await nav(page, section.label);
    await expect(page.getByRole("heading", { name: section.heading, level: 1 })).toBeVisible();
    await expect(page.getByText("Не удалось загрузить")).toHaveCount(0);
  }

  expect(errors).toEqual([]);
});

test("a run from the seeded database opens with a timeline", async ({ page }) => {
  await signedInAs(page, HR);
  await nav(page, "Сотрудники");

  // The demo data ships three runs; the first card is anyone's. The point is that the id in the
  // address resolves on the server, not that a particular person is first.
  await page.getByRole("main").getByRole("button").first().click();

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Хронология" })).toBeVisible();
  // A detail page opened by a session cookie, not by a token in the address.
  await expect(page).not.toHaveURL(/token=/);
});

test("a document from the corpus opens with its markdown", async ({ page }) => {
  await signedInAs(page, HR);
  await nav(page, "Знания");

  await page.getByRole("button", { name: /^Открыть документ/ }).first().click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  // The body is the markdown the index was built from, served by the API and rendered by nginx:
  // an empty body would mean the corpus and the cabinet disagree.
  await expect(dialog.locator("p, pre, li").first()).toBeVisible();
});
