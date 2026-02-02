import { test, expect } from "@playwright/test";

const BASE_URL = process.env.FRONTEND_URL || "http://localhost:3000";

test.describe("Authentication Flow", () => {
  test.describe("Route Protection", () => {
    test("unauthenticated access to /dashboard redirects to /login", async ({
      page,
    }) => {
      // Clear any existing session
      await page.context().clearCookies();

      // Try to access dashboard
      await page.goto(`${BASE_URL}/dashboard`);

      // Should redirect to login with callbackUrl
      await expect(page).toHaveURL(/\/login/);
      expect(page.url()).toContain("callbackUrl");
    });

    test("unauthenticated access to /dashboard/articles redirects to /login with callbackUrl", async ({
      page,
    }) => {
      await page.context().clearCookies();

      await page.goto(`${BASE_URL}/dashboard/articles`);

      await expect(page).toHaveURL(/\/login/);
      // Check that callbackUrl contains the original path
      const url = new URL(page.url());
      const callbackUrl = url.searchParams.get("callbackUrl");
      expect(callbackUrl).toContain("/dashboard");
    });

    test("unauthenticated access to /dashboard/settings redirects to /login", async ({
      page,
    }) => {
      await page.context().clearCookies();

      await page.goto(`${BASE_URL}/dashboard/settings`);

      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe("Landing Page", () => {
    test("Get Started button navigates to login page", async ({ page }) => {
      await page.goto(`${BASE_URL}/`);

      // Click the Get Started button
      await page.getByRole("link", { name: /get started/i }).click();

      // Should navigate to login
      await expect(page).toHaveURL(`${BASE_URL}/login`);
    });

    test("landing page does not have direct dashboard link", async ({
      page,
    }) => {
      await page.goto(`${BASE_URL}/`);

      // Check that there's no direct link to /dashboard (without auth)
      const dashboardLinks = await page
        .locator('a[href="/dashboard"]')
        .count();
      expect(dashboardLinks).toBe(0);
    });
  });

  test.describe("Login Page", () => {
    test("login page renders sign in form", async ({ page }) => {
      await page.goto(`${BASE_URL}/login`);

      await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();
      await expect(page.getByText("Continue with Google")).toBeVisible();
    });

    test("login page has Google OAuth button", async ({ page }) => {
      await page.goto(`${BASE_URL}/login`);

      const googleButton = page.getByRole("button", {
        name: /continue with google/i,
      });
      await expect(googleButton).toBeVisible();
      await expect(googleButton).toBeEnabled();
    });
  });

  test.describe("Public Routes", () => {
    test("landing page is accessible without authentication", async ({
      page,
    }) => {
      await page.context().clearCookies();

      await page.goto(`${BASE_URL}/`);

      // Should stay on landing page, not redirect
      await expect(page).toHaveURL(`${BASE_URL}/`);
      await expect(page.getByText("AI News Aggregator")).toBeVisible();
    });

    test("login page is accessible without authentication", async ({
      page,
    }) => {
      await page.context().clearCookies();

      await page.goto(`${BASE_URL}/login`);

      // Should stay on login page, not redirect
      await expect(page).toHaveURL(`${BASE_URL}/login`);
    });
  });
});
