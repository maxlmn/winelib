import type { Bottle } from './types';

/** One vintage on a line: its key leaves it out of the list (a wine in one format) */
export interface ListVintage {
	vintage: string;
	key: string;
}

/** One line of the wine list: a cuvée in one format, its vintages together. */
export interface ListLine {
	key: string;
	producer: string;
	cuvee: string;
	color: string | null;
	grapes: string[];
	format: string | null;
	vintages: ListVintage[];
}

export interface ListAppellation {
	/** null: the region's wines without an appellation */
	appellation: string | null;
	lines: ListLine[];
}

export interface ListRegion {
	region: string;
	appellations: ListAppellation[];
}

export interface ListSection {
	title: string;
	regions: ListRegion[];
}

/** A restaurant list's order: bubbles first, sweet and fortified last */
const SECTIONS: [string, string[]][] = [
	['Sparkling', ['Bubbles', 'Bubbles Rose']],
	['White', ['White']],
	['Orange', ['Orange']],
	['Rosé', ['Rose']],
	['Red', ['Red']],
	['Sweet & fortified', ['Sweet', 'Fortified']]
];

/** A wine in one format: what leaves one vintage out */
export const vintageKey = (b: Pick<Bottle, 'wine_id' | 'format'>) => `${b.wine_id}-${b.format ?? ''}`;

const cl = (format: string | null) => {
	const m = (format ?? '').toLowerCase().replace(/\s/g, '').match(/^(\d+(?:\.\d+)?)cl$/);
	return m ? Number(m[1]) : null;
};

/** A bottle size as a list prints it; nothing for a 75 cl bottle (or no format) */
export function formatName(format: string | null): string {
	const n = cl(format);
	if (n === null) return format ?? '';
	const named: Record<number, string> = { 37.5: 'Half bottle', 150: 'Magnum', 300: 'Double magnum', 600: 'Imperial' };
	return n === 75 ? '' : (named[n] ?? `${n} cl`);
}

const byText = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: 'base' });
/** NV after the years, the years oldest first */
const byVintage = (a: string, b: string) => (a === b ? 0 : !/^\d+$/.test(a) ? 1 : !/^\d+$/.test(b) ? -1 : Number(a) - Number(b));

function group<T>(items: T[], key: (t: T) => string): Map<string, T[]> {
	const out = new Map<string, T[]>();
	for (const t of items) out.set(key(t), [...(out.get(key(t)) ?? []), t]);
	return out;
}

/** The bottles as a list: sections by colour, then regions, appellations, and a line per cuvée and format with its
 * vintages. `leftOut` holds vintage keys. */
export function wineList(bottles: Bottle[], leftOut: Set<string> = new Set()): ListSection[] {
	const kept = bottles.filter((b) => !leftOut.has(vintageKey(b)));
	const known = new Set(SECTIONS.flatMap(([, colors]) => colors));
	const sections: [string, string[] | null][] = [...SECTIONS, ['Other', null]];
	return sections
		.map(([title, colors]) => {
			const mine = kept.filter((b) => (colors ? colors.includes(b.color ?? '') : !known.has(b.color ?? '')));
			const regions = [...group(mine, (b) => b.region)].sort(([a], [b]) => byText(a, b));
			return {
				title,
				regions: regions.map(([region, inRegion]) => ({
					region,
					appellations: [...group(inRegion, (b) => b.appellation ?? '')]
						// the region's own name first (Champagne in Champagne), then by name, none last
						.sort(([a], [b]) => Number(b === region) - Number(a === region) || Number(!a) - Number(!b) || byText(a, b))
						.map(([appellation, inAppellation]) => ({
							appellation: appellation || null,
							lines: [...group(inAppellation, (b) => `${b.producer}|${b.cuvee}|${b.format ?? ''}`)]
								.map(([key, bs]) => ({
									key,
									producer: bs[0].producer,
									cuvee: bs[0].cuvee,
									color: bs[0].color,
									grapes: bs[0].grapes,
									format: bs[0].format,
									vintages: [...new Map(bs.map((b) => [vintageKey(b), b.vintage]))]
										.map(([key, vintage]) => ({ key, vintage }))
										.sort((a, b) => byVintage(a.vintage, b.vintage))
								}))
								.sort(
									(a, b) =>
										byText(a.producer, b.producer) || byText(a.cuvee, b.cuvee) || (cl(a.format) ?? 75) - (cl(b.format) ?? 75)
								)
						}))
				}))
			};
		})
		.filter((s) => s.regions.length);
}
