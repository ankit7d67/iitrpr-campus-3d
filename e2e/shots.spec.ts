import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

/**
 * Visual QA shots for the reviewer (no vision model in the agent environment).
 * Runs as part of `make e2e`; writes build/preview/ui-desktop.png (chromium,
 * 1440x900) and build/preview/ui-phone.png (pixel7, 412x915) after every run.
 */
const OUT_DIR = path.resolve(__dirname, '..', 'build', 'preview');

test('capture UI screenshot for visual QA', async ({ page }, testInfo) => {
  const phone = testInfo.project.name === 'pixel7';
  const file = phone ? 'ui-phone.png' : 'ui-desktop.png';
  fs.mkdirSync(OUT_DIR, { recursive: true });
  await page.setViewportSize(phone ? { width: 412, height: 915 } : { width: 1440, height: 900 });

  const glb = page.waitForResponse((r) => r.url().includes('/models/campus.glb'));
  await page.goto('/');
  const res = await glb;
  expect(res.status()).toBe(200);
  await expect(page.locator('canvas').first()).toBeVisible();
  // give the model + campus data time to finish loading so the shot shows the campus
  await page.waitForTimeout(3000);

  await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: true });
  console.log(`SHOT_OK ${path.join(OUT_DIR, file)}`);
});
