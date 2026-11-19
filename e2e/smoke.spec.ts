import { test, expect } from '@playwright/test';

test('home page loads with title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/IIT Ropar/);
});

test('campus GLB is served and the canvas renders', async ({ page }) => {
  // A broken shader/texture (7-9 baked maps) still leaves a visible canvas, so
  // also fail on WebGL/material console errors.
  const glErrors: string[] = [];
  page.on('console', (m) => {
    if (m.type() === 'error' && /webgl|shader|glsl|material|texture|gl_/i.test(m.text())) {
      glErrors.push(m.text());
    }
  });
  const glb = page.waitForResponse((r) => r.url().includes('/models/campus.glb'));
  await page.goto('/');
  const res = await glb;
  expect(res.status()).toBe(200);
  expect(res.headers()['content-type'] ?? '').toContain('model/gltf-binary');
  await expect(page.locator('canvas').first()).toBeVisible();
  await page.waitForTimeout(1200);
  expect(glErrors, glErrors.join('\n')).toEqual([]);
});

test('served GLB uses Meshopt compression and WebP textures', async ({ page }) => {
  await page.goto('/');
  const info = await page.evaluate(async () => {
    const buf = await (await fetch('/models/campus.glb')).arrayBuffer();
    const view = new DataView(buf);
    const jsonLength = view.getUint32(12, true);
    const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 20, jsonLength)));
    return {
      extensions: json.extensionsUsed ?? [],
      images: (json.images ?? []).map((im: { mimeType?: string }) => im.mimeType),
      meshes: (json.meshes ?? []).length,
    };
  });
  expect(info.extensions).toContain('EXT_meshopt_compression');
  expect(info.extensions).toContain('EXT_texture_webp');
  expect(info.images).toEqual(['image/webp', 'image/webp']);
  expect(info.meshes).toBe(110);
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

test('loading screen shows progress while the model loads, then disappears', async ({ page }) => {
  // Delay the GLB so the loader is observable deterministically.
  await page.route('**/models/campus.glb', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 900));
    await route.continue();
  });
  await page.goto('/');
  const loader = page.getByTestId('loader');
  await expect(loader).toBeVisible();
  await expect(loader.getByRole('progressbar', { name: 'Loading the campus model' })).toBeVisible();
  await expect(loader).toBeHidden({ timeout: 15000 });
});

test('quality selector reports the effective tier and switches modes', async ({ page }) => {
  await page.goto('/');
  const select = page.locator('#quality');
  const effective = page.getByTestId('quality-effective');
  await expect(select).toHaveValue('auto');
  await expect(effective).toContainText('high');
  await select.selectOption('low');
  await expect(effective).toHaveText('low');
  await expect(page.locator('canvas').first()).toBeVisible();
  await select.selectOption('high');
  await expect(effective).toHaveText('high');
  await select.selectOption('auto');
  await expect(effective).toContainText('Auto · high');
});

test('building labels are visible and clicking one zooms into it', async ({ page }) => {
  await page.goto('/');
  const label = page.locator('[data-testid="map-label"]').filter({ hasText: 'Nalanda library' }).first();
  await expect(label).toBeVisible();
  await label.click();
  await expect(page.locator('.viewport')).toHaveAttribute('data-focus-id', 'BLDG_1349163385');
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(/Nalanda/i);
});

test('data fetch failure shows an actionable error card', async ({ page }) => {
  await page.route('**/data/campus.json', (route) => route.fulfill({ status: 500, body: 'fail' }));
  await page.goto('/');
  // Scope to our card: Next.js injects its own empty route-announcer [role=alert].
  const alert = page.locator('.loader-error[role="alert"]');
  await expect(alert).toContainText(/could not be loaded/i);
  await expect(alert.getByRole('button', { name: 'Retry' })).toBeVisible();
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
