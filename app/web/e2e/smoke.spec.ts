/** Smoke tests: the pages load without errors, and the clicks go where the app says they do (see e2e/setup.ts for
 * the cellar they run on). */
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const ids = () => JSON.parse(readFileSync('e2e/.data/ids.json', 'utf-8'));

/** The page's errors (uncaught, or logged as errors), the map's tiles aside: CI may not reach them */
function errorsOf(page: Page) {
	const errors: string[] = [];
	page.on('pageerror', (e) => errors.push(e.message));
	page.on('console', (m) => {
		if (m.type() === 'error' && !/tiles|openfreemap|arcgis|ign\.fr|Failed to load resource|WebGL/i.test(m.text())) errors.push(m.text());
	});
	return errors;
}

test('the main pages load without errors', async ({ page }) => {
	const errors = errorsOf(page);
	for (const path of ['/', '/cellar', '/tastings', '/lists', '/map', '/settings']) {
		await page.goto(path);
		await expect(page.locator('main')).toBeVisible();
	}
	expect(errors).toEqual([]);
});

test("a wine's map: its legend shows and hides each shape, its names zoom", async ({ page }) => {
	const errors = errorsOf(page);
	await page.goto(`/wines/${ids().wine}`);
	const legend = page.locator('.keys .key');
	await expect(legend).toHaveCount(2); // its appellation and its vineyard
	const swatch = legend.first().locator('button.sw');
	await expect(swatch).toHaveAttribute('aria-pressed', 'true');
	await swatch.click();
	await expect(swatch).toHaveAttribute('aria-pressed', 'false');
	await expect(legend.first()).toHaveClass(/hidden/);
	await swatch.click();
	await expect(swatch).toHaveAttribute('aria-pressed', 'true');
	await legend.first().locator('button.name').click();
	await expect(legend.first()).toHaveClass(/\bon\b/); // zoomed to
	expect(errors).toEqual([]);
});

test('a wine without an outline keeps its page as it is', async ({ page }) => {
	await page.goto(`/wines/${ids().plainWine}`);
	// "No boundary data…", or "No map outlines installed yet" where none are (CI)
	await expect(page.locator('.empty').filter({ hasText: /No boundary data|No map outlines/ })).toBeVisible();
	expect(await page.evaluate(() => document.documentElement.classList.contains('map-full'))).toBe(false);
});

test("a tasting without a note opens from its \"No note\"; the page says it's a tasting", async ({ page }) => {
	await page.goto(`/wines/${ids().wine}`);
	await page.getByRole('tab', { name: /History/ }).click();
	const note = page.locator('a.note.empty').first();
	await expect(note).toContainText('No note');
	await note.click();
	await expect(page).toHaveURL(new RegExp(`/tastings/${ids().tasting}$`));
	await expect(page.locator('.kind').first()).toHaveText(/Tasting/i);
});

test("a tasting card's date opens the occasion in the journal", async ({ page }) => {
	await page.goto(`/wines/${ids().wine}`);
	await page.getByRole('tab', { name: /History/ }).click();
	await page.locator('a.date').first().click();
	await expect(page).toHaveURL(/\/tastings\?.*from=2026-10-01.*to=2026-10-01/);
	await expect(page.getByText('Le Bourg').first()).toBeVisible();
});

test("the cellar's wine label opens the bottle", async ({ page }) => {
	await page.goto('/cellar?view=list');
	await page.getByRole('link', { name: 'Le Bourg' }).first().click();
	await expect(page).toHaveURL(new RegExp(`/bottles/${ids().bottle}$`));
	await expect(page.locator('.kind').first()).toHaveText(/Bottle/i);
});

test('Fill from text fills the new-bottle form', async ({ page }) => {
	await page.goto('/bottles/new');
	await page.getByRole('button', { name: /Fill from text/ }).click();
	await page.locator('#b-text').fill(
		"Vous remportez l'enchère du lot de la vente du 29/10/2026 (iDealwine) : 2 Bouteilles Clos Rougeard Le Bourg Rouge 2019\nPrix d'adjudication : 680,00 €"
	);
	await page.getByRole('button', { name: 'Fill', exact: true }).click();
	await expect(page.locator('.fill .found')).toContainText('a new vintage of a cuvée you have');
	await expect(page.locator('#b-qty')).toHaveValue('2');
	await expect(page.locator('#b-vendor')).toHaveValue('Idealwine');
	await expect(page.locator('#b-date')).toHaveValue('2026-10-29');
	await expect(page.locator('#b-price')).toHaveValue('340'); // the lot's 680 for 2 bottles
});

test('a phone: no page wider than the screen', async ({ page }) => {
	await page.setViewportSize({ width: 375, height: 812 });
	for (const path of ['/', `/wines/${ids().wine}`, '/cellar', '/tastings']) {
		await page.goto(path);
		await expect(page.locator('main')).toBeVisible();
		const wide = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
		expect(wide, path).toBeLessThanOrEqual(1);
	}
});

test('Settings › Needs attention opens its check in Maintenance, the preview run', async ({ page }) => {
	await page.goto('/settings');
	await page.getByRole('tab', { name: /Needs attention/ }).click();
	const panel = page.getByRole('region', { name: 'Needs attention' });
	await expect(panel).toContainText('1 wine entered twice');
	await panel.getByRole('link', { name: /entered twice/ }).click();
	await expect(page).toHaveURL(/\/settings\?tab=maintenance&task=duplicates/);
	await expect(page.getByRole('tab', { name: 'Maintenance' })).toHaveAttribute('aria-selected', 'true');
	await expect(page.getByText('1 group of duplicate wines')).toBeVisible({ timeout: 15_000 });
});
