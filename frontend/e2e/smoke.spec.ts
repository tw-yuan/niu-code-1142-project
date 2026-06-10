import { expect, test } from "@playwright/test";

test("login page renders the learning assistant entry point", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("學業輔助")).toBeVisible();
  await expect(page.getByRole("button", { name: /登入/ })).toBeVisible();
});

test("protected pages redirect unauthenticated users to login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/history");
  await expect(page).toHaveURL(/\/login/);
});
