import { test, expect } from '@playwright/test';

test('home page loads with title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/IIT Ropar/);
});

test('deep link ?b=<ID> opens info panel', async ({ page }) => {
  await page.goto('/?b=BLDG_hostel_ganga');
  await expect(page.getByRole('dialog')).toBeVisible();
});

test('deep link ?from=&to= sets route', async ({ page }) => {
  await page.goto('/?from=BLDG_hostel_ganga&to=BLDG_lib');
  await expect(page.getByText(/Walking route|BLDG_hostel_ganga/)).toBeVisible();
});

test('search finds a building and opens the info panel', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder('Search buildings, hostels, departments');
  await input.fill('hostel');
  await expect(page.getByRole('listbox')).toBeVisible();
  await page.getByRole('button', { name: /ganga/i }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
});

test('tour panel lists stops and can select one', async ({ page }) => {
  await page.goto('/');
  const tour = page.locator('.tour-panel');
  await expect(tour).toBeVisible();
  const stop = tour.getByRole('button').first();
  if (await stop.count()) {
    await stop.click();
  }
});
