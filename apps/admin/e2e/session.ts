import { expect, type Page } from "@playwright/test";

export const RECRUITER = "dev-recruiter-token";
export const HR = "dev-hr-token";

/** The gate is the only way in: a token becomes an HttpOnly cookie and never touches storage. */
export async function signIn(page: Page, token: string): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Токен доступа").fill(token);
  await page.getByRole("button", { name: "Войти в кабинет" }).click();
  await expect(page.getByRole("navigation", { name: "Разделы кабинета" })).toBeVisible();
}

export async function signedInAs(page: Page, token: string): Promise<void> {
  const cookies = await page.context().cookies();
  if (cookies.some((cookie) => cookie.name === "onboarding_session")) {
    await page.goto("/");
    await expect(page.getByRole("navigation", { name: "Разделы кабинета" })).toBeVisible();
    return;
  }
  await signIn(page, token);
}

/** The sidebar button, not the "Все сотрудники" link that happens to share the word. */
export async function nav(page: Page, label: string): Promise<void> {
  await page.getByRole("navigation", { name: "Разделы кабинета" }).getByRole("button", { name: label }).click();
}
