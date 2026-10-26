/** Pips for the region strips (RegionStrip): a bottle or a tasting each, with what the hover card says. */
import type { Pip } from '#lib/components/RegionStrip.svelte';
import type { Tasting } from '#lib/api/details.ts';
import type { Bottle } from '#lib/types.ts';
import { links } from '#lib/links.ts';
import { fmtDay } from '#lib/components/tastings/journal.ts';

const wine = (w: { producer: string; cuvee: string; vintage: string }) => `${w.producer}${w.cuvee ? ` – ${w.cuvee}` : ''} ${w.vintage}`;
const byRegion = (a: Pip, b: Pip) => (a.region ?? '').localeCompare(b.region ?? '');

/** A pip per bottle in the cellar (qty of them per line), keyed by the line */
export const bottlePips = (bottles: Bottle[]): Pip[] =>
	bottles.flatMap((b) =>
		Array.from({ length: b.qty }, () => ({
			region: b.region,
			color: b.color,
			format: b.format,
			label: wine(b),
			sub: [b.appellation, b.location].filter(Boolean).join(' · '),
			href: links.bottle(b.bottle_id),
			key: b.bottle_id
		}))
	);

/** A pip per tasting */
export const tastingPips = (tastings: Tasting[]): Pip[] =>
	tastings.map((t) => ({
		region: t.region,
		color: t.color,
		format: t.format,
		label: wine(t),
		sub: [t.date && fmtDay(t.date), t.place?.name ?? t.location].filter(Boolean).join(' · '),
		href: links.tasting(t.id),
		key: t.id
	}));

/** Grouped by region, so each region reads as one block of its color */
export const sortedByRegion = (pips: Pip[]) => [...pips].sort(byRegion);
