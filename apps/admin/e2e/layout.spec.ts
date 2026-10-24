import { expect, test } from "@playwright/test";

import { HR, signedInAs } from "./session";

/**
 * Layout invariants, asserted at whatever viewport the project runs.
 *
 * `playwright.config.ts` runs this file on a desktop, an iPad (icon rail) and a phone in both
 * orientations, so a stylesheet change that only works at 1280px fails here.
 */
const SCREENS: ReadonlyArray<{ name: string; hash: string }> = [
  { name: "overview", hash: "#/overview" },
  { name: "runs", hash: "#/runs" },
  { name: "run detail", hash: "#/run/4a1d2c3b-5e6f-4a71-8b92-0c1d2e3f4a5b" },
  { name: "questions", hash: "#/questions" },
  { name: "risk", hash: "#/risk" },
  { name: "knowledge", hash: "#/knowledge" },
];

const PHONE_SHELL = "(max-width: 760px), (max-height: 560px) and (pointer: coarse)";

/** Elements sticking out of the viewport: a wrapped title, a badge, an unbreakable id. */
async function overflowingElements(page: import("@playwright/test").Page): Promise<string[]> {
  return page.evaluate(() => {
    const width = window.innerWidth;
    const found: string[] = [];
    for (const element of Array.from(document.querySelectorAll<HTMLElement>("body *"))) {
      const box = element.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) continue;
      if (box.right <= width + 1 && box.left >= -1) continue;
      // A deliberate horizontal scroller inside a card is allowed to be wider than its parent.
      const style = getComputedStyle(element);
      if (style.overflowX === "auto" || style.overflowX === "scroll") continue;
      found.push(
        `<${element.tagName.toLowerCase()} class="${element.className}"> right=${Math.round(box.right)}`,
      );
    }
    return found;
  });
}

test.describe("shell", () => {
  test("the page itself never scrolls, so the shell stays put", async ({ page }) => {
    await signedInAs(page, HR);
    const scroll = await page.evaluate(() => ({
      vertical: document.documentElement.scrollHeight - document.documentElement.clientHeight,
      horizontal: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }));
    expect(scroll).toEqual({ vertical: 0, horizontal: 0 });
  });

  test("navigation buttons keep the label as their accessible name", async ({ page }) => {
    await signedInAs(page, HR);
    for (const label of ["Обзор", "Сотрудники", "Вопросы", "Риски", "Знания"]) {
      const button = page
        .getByRole("navigation", { name: "Разделы кабинета" })
        .getByRole("button", { name: label });
      // The rail clips the label but must not drop it, and the unread badge must not replace it.
      await expect(button).toHaveAccessibleName(new RegExp(`^${label}`));
    }
  });

  test("the shell adopts the shape its width allows", async ({ page }) => {
    await signedInAs(page, HR);
    const phoneShell = await page.evaluate((query) => window.matchMedia(query).matches, PHONE_SHELL);
    const shell = await page.evaluate(() => {
      const sidebar = document.querySelector<HTMLElement>(".sidebar")!;
      const app = document.querySelector<HTMLElement>(".app")!;
      const style = getComputedStyle(sidebar);
      return {
        position: style.position,
        sidebarBottom: Math.round(sidebar.getBoundingClientRect().bottom),
        sidebarWidth: Math.round(sidebar.getBoundingClientRect().width),
        viewportHeight: window.innerHeight,
        appColumns: getComputedStyle(app).gridTemplateColumns,
      };
    });

    if (phoneShell) {
      expect(shell.position).toBe("fixed");
      expect(shell.sidebarBottom).toBe(shell.viewportHeight);
      expect(shell.sidebarWidth).toBeGreaterThan(200);
      // The bar covers the last rows of a list unless the scroll container reserves its height.
      const reserved = await page.evaluate(() =>
        parseFloat(getComputedStyle(document.querySelector<HTMLElement>(".content")!).paddingBottom),
      );
      expect(reserved).toBeGreaterThanOrEqual(64);
      await expect(page.getByRole("button", { name: "Выйти" })).toBeVisible();
    } else {
      expect(shell.position).not.toBe("fixed");
      expect(shell.sidebarWidth).toBeLessThanOrEqual(248);
    }
  });

  test("log out is reachable without scrolling the page", async ({ page }) => {
    await signedInAs(page, HR);
    const logout = page.getByRole("button", { name: "Выйти" }).first();
    await logout.scrollIntoViewIfNeeded();
    await expect(logout).toBeInViewport();
  });
});

for (const screen of SCREENS) {
  test(`${screen.name} fits the viewport`, async ({ page }) => {
    await signedInAs(page, HR);
    await page.goto(`/${screen.hash}`);
    await page.getByRole("heading", { level: 1 }).first().waitFor();

    expect(await overflowingElements(page)).toEqual([]);
    const horizontal = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(horizontal).toBeLessThanOrEqual(0);
  });
}

test("tappable controls are at least 24px tall on a touch screen", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.use.hasTouch, "a mouse can hit a 20px link; a finger cannot");
  await signedInAs(page, HR);
  await page.goto("/#/questions");
  await page.getByRole("heading", { level: 1 }).first().waitFor();

  const tooSmall = await page.evaluate(() => {
    const small: string[] = [];
    const controls = document.querySelectorAll<HTMLElement>(
      "button, a[href], input, select, [role=tab], [role=button]",
    );
    for (const control of Array.from(controls)) {
      const box = control.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) continue;
      if (box.height >= 24 && box.width >= 24) continue;
      small.push(`${control.tagName}.${control.className} ${Math.round(box.width)}x${Math.round(box.height)}`);
    }
    return small;
  });
  expect(tooSmall).toEqual([]);
});
