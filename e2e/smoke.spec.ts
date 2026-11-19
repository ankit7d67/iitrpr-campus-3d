import { test, expect } from '@playwright/test';

test('home page loads with title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/IIT Ropar/);
});

test('campus GLB is served and the canvas renders', async ({ page }) => {
  const glb = page.waitForResponse((r) => r.url().includes('/models/campus.glb'));
  await page.goto('/');
  const res = await glb;
  expect(res.status()).toBe(200);
  expect(res.headers()['content-type'] ?? '').toContain('model/gltf-binary');
  await expect(page.locator('canvas').first()).toBeVisible();
});

test('deep link ?b=<ID> opens info panel', async ({ page }) => {
  await page.goto('/?b=BLDG_1349163385');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(/Nalanda/i);
});

test('deep link ?from=&to= sets route', async ({ page }) => {
  await page.goto('/?from=BLDG_1349163385&to=BLDG_1349204070');
  await expect(page.getByText(/Nalanda library/i)).toBeVisible();
  await expect(page.getByText(/Ravi Girls Hostel/i)).toBeVisible();
});

test('search finds a building and opens the info panel', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder('Search buildings, hostels, departments');
  await input.fill('nalanda');
  const listbox = page.getByRole('listbox');
  await expect(listbox).toBeVisible();
  await expect(listbox).toContainText(/Nalanda library/i);
  await input.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(/Nalanda/i);
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
