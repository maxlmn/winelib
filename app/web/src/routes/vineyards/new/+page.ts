import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export interface NewVineyardStart {
	frame: [number, number, number, number] | null;
	name: string;
	region: string | null;
	appellation: string | null;
	wine: { id: number; producer: string; cuvee: string; vintage: string; vineyard_id: number | null };
}

export const load: PageLoad = async ({ fetch, url }) => {
	const wine = url.searchParams.get('wine');
	if (!wine || !/^\d+$/.test(wine)) error(404, 'Draw a vineyard from a wine’s page');
	const res = await fetch(`/api/wines/${wine}/new-vineyard`);
	if (!res.ok) error(res.status === 404 ? 404 : res.status, res.status === 404 ? 'Wine not found' : 'Couldn’t load the wine');
	return { start: (await res.json()) as NewVineyardStart };
};
