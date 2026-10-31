/** The smoke tests' cellar, made through the app's API on a new installation (playwright.config.ts): settings saved,
 * a Saumur-Champigny with drawn outlines (its appellation and its vineyard) and a bottle tasted without a note, and
 * a wine whose appellation has no outline. Their ids go to e2e/.data/ids.json for the tests. */
import { request, type FullConfig } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';

const square = (x: number, y: number, d: number) => ({
	type: 'Polygon',
	coordinates: [[[x, y], [x + d, y], [x + d, y + d], [x, y + d], [x, y]]]
});

export default async function setup(config: FullConfig) {
	const api = await request.newContext({ baseURL: config.projects[0].use.baseURL });
	const ok = async (r: Awaited<ReturnType<typeof api.get>>) => {
		if (!r.ok()) throw new Error(`${r.url()}: ${r.status()} ${await r.text()}`);
		return r.json();
	};
	await ok(await api.put('/api/settings', { data: await ok(await api.get('/api/settings/defaults')) }));
	const appellation = async (q: string) => (await ok(await api.get('/api/lookups/appellations', { params: { q } })))[0];
	const sc = await appellation('Saumur-Champigny');
	const other = await appellation('Chinon');

	await ok(await api.put(`/api/appellations/${sc.id}/outline`, { data: { geometry: square(-0.1, 47.2, 0.1) } }));
	const bottle = await ok(await api.post('/api/bottles', {
		data: {
			wine: { producer: { name: 'Clos Rougeard' }, cuvee: 'Le Bourg', vintage: '2016', type: 'Red', appellation: sc.id },
			qty: 3, location: 'R1', price: 300, currency: 'EUR', vendor: 'Idealwine'
		}
	}));
	const vineyard = await ok(await api.post('/api/vineyards', {
		data: { wine: bottle.wine_id, name: 'Le Bourg', village: 'Chacé', geometry: square(-0.07, 47.23, 0.01) }
	}));
	const tasting = await ok(await api.post('/api/tastings', {
		data: { source: 'cellar', bottle_id: bottle.id, date: '2026-10-01', consume: true, notes: '' }
	}));
	const plain = await ok(await api.post('/api/bottles', {
		data: { wine: { producer: { name: 'Domaine Sans Carte' }, cuvee: '', vintage: '2020', type: 'Red', appellation: other.id }, qty: 1, location: 'R2' }
	}));
	// a wine entered twice: the home page's Needs attention lists it
	for (let i = 0; i < 2; i++)
		await ok(await api.post('/api/wines', { data: { producer: { name: 'Domaine Double' }, cuvee: 'Bis', vintage: '2019', type: 'White' } }));
	// sparkling wines with their disgorgement, a vintage and an NV: under the appellation
	const sparkling = (cuvee: string, vintage: string, type: string, disgorgement_date: string) =>
		api.post('/api/wines', { data: { producer: { name: 'Maison Rosée' }, cuvee, vintage, type, disgorgement_date } });
	const rose = await ok(await sparkling('Brut Rosé', '2012', 'Bubbles Rose', 'Oct 2024'));
	const nv = await ok(await sparkling('Brut', 'NV', 'Bubbles', 'Mar 2023'));
	mkdirSync('e2e/.data', { recursive: true });
	writeFileSync('e2e/.data/ids.json', JSON.stringify({
		wine: bottle.wine_id, bottle: bottle.id, vineyard: vineyard.id, tasting: tasting.id, plainWine: plain.wine_id, rose: rose.id, nv: nv.id
	}));
	await api.dispose();
}
