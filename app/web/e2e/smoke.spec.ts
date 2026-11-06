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

test("the home page's dice opens one of your wines", async ({ page }) => {
	await page.goto('/');
	await page.getByRole('button', { name: 'A wine at random' }).click();
	await expect(page).toHaveURL(/\/wines\/\d+$/);
	await expect(page.locator('main h1')).toBeVisible();
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

test("a region's map draws your appellations and vineyards, not only its top list's", async ({ page }) => {
	const errors = errorsOf(page);
	await page.goto('/regions/Loire');
	const legend = page.locator('.keys .key');
	await expect(legend.filter({ hasText: 'Saumur-Champigny' })).toHaveCount(1);
	await expect(legend.filter({ hasText: 'Le Bourg' })).toHaveCount(1); // the vineyard you hold
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
	// the bottle: the band at the foot of its wine's card; its line marked in the Cellar tab
	await expect(page.locator('.foot .line1')).toContainText(/bottles? · In R1/);
	await page.getByRole('tab', { name: /Cellar/ }).click();
	await expect(page.locator('li.current')).toContainText('this bottle');
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

// Claude isn't called: the options say a key is set, and the server's reading is the test's
test('Fill from photos sends the labels shrunk to JPEG and fills the new-bottle form', async ({ page }) => {
	await page.route('**/api/lookups/options', async (route) => {
		const r = await route.fetch();
		await route.fulfill({ response: r, json: { ...(await r.json()), label_photos: true } });
	});
	let sent: { side: string; media_type: string; data: string }[] = [];
	await page.route('**/api/lookups/from-photos', (route) => {
		sent = route.request().postDataJSON().photos;
		return route.fulfill({
			json: {
				line: 'Maison Photo Blanc de Blancs 2015', producer: { id: null, name: 'Maison Photo' }, cuvee: 'Blanc de Blancs',
				vintage: '2015', type: 'Bubbles', size: null, appellation: null, region: null, wine_id: null, like_id: null,
				qty: null, price: null, currency: null, price_total: null, purchase_date: null, vendor: null,
				disgorgement_date: 'Mar 2024', not_read: ['size'], note: 'Vintage read from the neck label'
			}
		});
	});
	await page.goto('/bottles/new');
	await page.getByRole('button', { name: /Fill from photos/ }).click();
	// a 2×2 PNG for each label
	const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGP4z8DAwMDAwMDAwMDAAAANAAEUY7mBAAAAAElFTkSuQmCC', 'base64');
	await page.getByLabel('Photo of the back label').locator('input').setInputFiles({ name: 'back.png', mimeType: 'image/png', buffer: png });
	await page.getByLabel('Photo of the front label').locator('input').setInputFiles({ name: 'front.png', mimeType: 'image/png', buffer: png });
	await expect(page.locator('.shot img')).toHaveCount(2);
	await page.getByRole('button', { name: 'Fill', exact: true }).click();
	await expect(page.locator('.fill .found')).toContainText('a new wine');
	await expect(page.locator('.fill .found')).toContainText('Not read: size. Vintage read from the neck label');
	expect(sent.map((p) => [p.side, p.media_type])).toEqual([['front', 'image/jpeg'], ['back', 'image/jpeg']]);
	expect(Buffer.from(sent[0].data, 'base64').subarray(0, 2)).toEqual(Buffer.from([0xff, 0xd8])); // a JPEG
	await expect(page.locator('#b-new-vintage')).toHaveValue('2015');
	await expect(page.locator('#b-new-cuvee')).toHaveValue('Blanc de Blancs');
	await expect(page.getByLabel('Disgorgement date')).toHaveValue('Mar 2024');
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
	// the preview started once: not again each time the job ends and the tasks reload
	let starts = 0;
	page.on('request', (r) => {
		if (r.method() === 'POST' && r.url().endsWith('/api/maintenance/duplicates')) starts++;
	});
	const panel = page.getByRole('region', { name: 'Needs attention' });
	await expect(panel).toContainText('1 wine entered twice');
	await panel.getByRole('link', { name: /entered twice/ }).click();
	await expect(page).toHaveURL(/\/settings\?tab=maintenance&task=duplicates/);
	await expect(page.getByRole('tab', { name: 'Maintenance' })).toHaveAttribute('aria-selected', 'true');
	await expect(page.getByText('1 wine entered more than once').first()).toBeVisible({ timeout: 15_000 });
	await page.waitForTimeout(3000);
	expect(starts).toBe(1);
});

test("a wine's menu sets its drinking window", async ({ page }) => {
	await page.goto(`/wines/${ids().plainWine}`);
	await page.locator('header.head .action-menu > button').click();
	await page.getByRole('menuitem', { name: /drinking window/ }).click();
	await page.getByLabel('From').fill('2026');
	await page.getByLabel('To').fill('2035');
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.locator('header.head .about')).toContainText('Drink 2026–2035');
});

test("a sparkling wine's disgorgement: its year after the vintage, the date in its tooltip; set in its form, a new vintage's too", async ({ page }) => {
	const disg = page.locator('header.head .disg');
	await page.goto(`/wines/${ids().nv}`);
	await expect(page.locator('header.head .vintage')).toHaveText('NV');
	await expect(disg).toHaveText('Disg. 23');
	await page.goto(`/wines/${ids().rose}`);
	await expect(disg).toHaveText('Disg. 24');
	await expect(disg).toHaveAttribute('title', 'Disgorged Oct 2024');
	await page.goto(`/wines/${ids().rose}/edit`);
	await page.getByLabel('Disgorgement date').fill('Jan 2025');
	await page.getByRole('button', { name: 'Save wine' }).click();
	await expect(disg).toHaveText('Disg. 25');
	// adding a bottle of another vintage of it: its form asks for the new one's disgorgement
	await page.goto(`/bottles/new?wine_id=${ids().rose}`);
	await page.getByRole('button', { name: /New vintage/ }).click();
	await expect(page.getByLabel('Disgorgement date')).toHaveValue('');
});

// the app on plain http (a NAS): no crypto.randomUUID there, outside https and localhost
test('a vineyard outline imported over plain http is drawn on the map', async ({ page }) => {
	await page.addInitScript(() => Object.defineProperty(crypto, 'randomUUID', { value: undefined }));
	const errors: string[] = [];
	page.on('pageerror', (e) => errors.push(e.message));
	await page.goto(`/wines/${ids().plainWine}`);
	await page.locator('header.head .action-menu > button').click();
	await page.getByRole('menuitem', { name: /vineyard/ }).click();
	const tools = page.getByRole('toolbar');
	await expect(tools).toContainText('nothing drawn yet');
	const square = { type: 'Polygon', coordinates: [[[0.2, 47.1], [0.21, 47.1], [0.21, 47.11], [0.2, 47.11], [0.2, 47.1]]] };
	await tools.locator('input[type=file]').setInputFiles({ name: 'v.geojson', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(square)) });
	await expect(tools).toContainText('1 shape');
	expect(errors).toEqual([]);
});

// last: it merges the seeded duplicate
test('Needs attention checks again after a task fixed what it found', async ({ page }) => {
	await page.goto('/settings?tab=attention');
	const panel = page.getByRole('region', { name: 'Needs attention' });
	await expect(panel).toContainText('entered twice');
	await page.getByRole('tab', { name: 'Maintenance' }).click();
	page.on('dialog', (d) => d.accept());
	await page.locator('#task-duplicates').getByRole('button', { name: 'Run' }).click();
	await expect(page.getByText(/duplicate deleted/).first()).toBeVisible({ timeout: 15_000 });
	await page.getByRole('tab', { name: /Needs attention/ }).click();
	await expect(panel).not.toContainText('entered twice');
});

// (desktop Chromium scrolls them even when a phone's touch scrolling doesn't: a basic check, not that one)
test('a phone, the map full size: the cards over it scroll', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 700 });
	await page.goto(`/wines/${ids().wine}`);
	const full = page.getByRole('button', { name: /Full map/ });
	if (await full.count()) await full.click();
	const card = page.locator('main .card.vintages');
	await expect(card).toBeVisible();
	const box = (await card.boundingBox())!;
	await page.mouse.move(box.x + box.width / 2, box.y + 10);
	await page.mouse.wheel(0, 300);
	await expect.poll(() => page.evaluate(() => document.querySelector('main')!.scrollTop)).toBeGreaterThan(0);
});

test("a grape's page: its description in its one card, the family beside it, the sources' credits", async ({ page }) => {
	const errors = errorsOf(page);
	await page.goto('/grapes/Cabernet%20Sauvignon');
	const card = page.locator('header.card section.about');
	await expect(card.getByRole('heading', { name: 'Origin' })).toBeVisible();
	await expect(page.getByText('Origin', { exact: true })).toHaveCount(1); // said once, not also as a fact
	await expect(card.getByRole('heading', { name: 'Ripening' })).toHaveCount(0); // the vine's sections wait for "More"
	await card.getByRole('button', { name: 'More' }).click();
	await expect(card.getByRole('heading', { name: 'Ripening' })).toBeVisible();
	await expect(card.getByText("Where it's planted")).toBeVisible();
	await expect(card.getByText(/Pl@ntGrape, Catalogue of Vines/)).toBeVisible();
	const side = (await page.locator('section.family').boundingBox())!;
	const main = (await page.locator('header.card').boundingBox())!;
	expect(side.x).toBeGreaterThan(main.x + main.width - 1);
	expect(Math.abs(side.width - main.width)).toBeLessThan(2); // half each
	const tabs = (await page.getByRole('tab', { name: /History/ }).boundingBox())!;
	expect(tabs.x).toBeGreaterThan(main.x + main.width - 1); // your wines under the family
	expect(tabs.y).toBeGreaterThan(side.y + side.height - 1);
	await expect(page.locator('section.family a', { hasText: 'Cabernet Franc' })).toBeVisible();
	if (process.env.SHOT) await page.screenshot({ path: process.env.SHOT, fullPage: true });
	expect(errors).toEqual([]);
});
