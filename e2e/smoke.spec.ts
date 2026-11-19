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
  // Scope to the route panel: the tour list also shows these building names.
  const panel = page.locator('.panel').filter({ hasText: 'Walking route' });
  await expect(panel).toContainText(/Nalanda library → Ravi Girls Hostel/i);
});

test('route planner plans a route from the pickers', async ({ page }) => {
  await page.goto('/');
  const panel = page.locator('.panel').filter({ hasText: 'Walking route' });
  await expect(panel).toBeVisible();
  await panel.locator('select').nth(0).selectOption({ label: 'Nalanda library' });
  await panel.locator('select').nth(1).selectOption({ label: 'Ravi Girls Hostel' });
  await panel.getByRole('button', { name: 'Route', exact: true }).click();
  await expect(panel).toContainText(/Nalanda library → Ravi Girls Hostel/i);
  await expect(panel.locator('.route-steps li').first()).toBeVisible();
  await panel.getByRole('button', { name: 'Clear' }).click();
  await expect(panel.getByRole('button', { name: 'Route', exact: true })).toBeVisible();
});

test('sun panel shows solar info and reacts to time changes', async ({ page }) => {
  await page.goto('/');
  const sun = page.locator('.sun-panel');
  await expect(sun).toBeVisible();
  const elev = sun.locator('.sun-elevation');
  await expect(elev).toContainText('Elevation');
  await expect(sun).toContainText(/Sunrise \d\d:\d\d · sunset \d\d:\d\d/);
  const before = await elev.innerText();
  await sun.locator('#sun-time').fill('2026-06-15T12:30');
  await expect(elev).not.toHaveText(before);
  await sun.getByRole('button', { name: 'Now' }).click();
  await expect(elev).not.toHaveText(before);
});

test('sky and street lamps switch on at night', async ({ page }) => {
  await page.goto('/');
  const lamps = page.getByTestId('lamp-status');
  await expect(lamps).toContainText('off');
  const sun = page.locator('.sun-panel');
  await sun.locator('#sun-time').fill('2026-06-15T22:00');
  await expect(lamps).toContainText('lit');
  await expect(page.locator('canvas').first()).toBeVisible();
  await sun.locator('#sun-time').fill('2026-06-15T12:30');
  await expect(lamps).toContainText('off');
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

test('tour panel lists stops, shows notes and moves between them', async ({ page }) => {
  await page.goto('/');
  const tour = page.locator('.tour-panel');
  await expect(tour).toBeVisible();
  await expect(tour.locator('ol li')).toHaveCount(9);
  await expect(tour.locator('.tour-note-text')).toHaveText('Lecture Hall (academic).');
  await expect(tour.locator('.tour-counter')).toHaveText('1 / 9');
  await tour.locator('ol li button').nth(1).click();
  await expect(tour.locator('.tour-note-text')).toHaveText('Super Academic Building (academic).');
  await expect(tour.locator('.tour-counter')).toHaveText('2 / 9');
  await tour.getByRole('button', { name: 'Next' }).click();
  await expect(tour.locator('.tour-note-text')).toHaveText('Nalanda Library (academic).');
  await expect(tour.locator('.tour-counter')).toHaveText('3 / 9');
  await tour.getByRole('button', { name: 'Prev' }).click();
  await expect(tour.locator('.tour-counter')).toHaveText('2 / 9');
});

test('drawer collapses and reopens with controls', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder('Search buildings, hostels, departments');
  await expect(input).toBeVisible();
  await page.getByRole('button', { name: 'Close controls' }).click();
  await expect(input).not.toBeVisible();
  await page.getByRole('button', { name: 'Open controls' }).click();
  await expect(input).toBeVisible();
});
