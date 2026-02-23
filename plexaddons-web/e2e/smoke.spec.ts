import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test('loads and shows title', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/PlexAddons/i);
  });

  test('has navigation links', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('link', { name: /addons/i })).toBeVisible();
  });

  test('can navigate to addons page', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('link', { name: /addons/i }).first().click();
    await expect(page).toHaveURL(/\/addons/);
  });
});

test.describe('Addons Page', () => {
  test('loads addon listing', async ({ page }) => {
    await page.goto('/addons');
    await expect(page.locator('h1, h2').first()).toBeVisible();
  });

  test('has search functionality', async ({ page }) => {
    await page.goto('/addons');
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible()) {
      await searchInput.fill('test');
      // Verify search triggers (no error)
      await expect(searchInput).toHaveValue('test');
    }
  });
});

test.describe('Auth', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('body')).toBeVisible();
  });

  test('unauthenticated user redirected from dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
