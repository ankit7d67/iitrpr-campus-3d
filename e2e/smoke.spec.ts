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
