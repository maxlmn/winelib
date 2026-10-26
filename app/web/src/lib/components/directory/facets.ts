/** Directory filters: faceted multi-selects + text search, all kept in the URL. */
export interface Facet<T> {
	key: string;
	label: string;
	values: (row: T) => (string | null | undefined)[];
	swatch?: (value: string) => string | undefined;
}

export type Selection = Record<string, string[]>;

type Params = Pick<URLSearchParams, 'getAll'>;

export const readSelection = <T>(params: Params, facets: Facet<T>[]): Selection =>
	Object.fromEntries(facets.map((f) => [f.key, params.getAll(f.key)]));

/** Rows matching every facet with a selection (values within a facet are OR-ed), optionally ignoring one facet. */
export function applyFacets<T>(rows: T[], facets: Facet<T>[], sel: Selection, except?: string): T[] {
	const active = facets.filter((f) => f.key !== except && sel[f.key]?.length);
	if (!active.length) return rows;
	return rows.filter((r) => active.every((f) => f.values(r).some((v) => v && sel[f.key].includes(v))));
}

/**
 * Options for one facet, counted over the rows the *other* facets let through, so picking a region narrows
 * the sub-regions on offer. Selected values stay listed (at 0) so they can always be unticked.
 */
export function facetOptions<T>(rows: T[], facets: Facet<T>[], sel: Selection, facet: Facet<T>) {
	const counts = new Map<string, number>((sel[facet.key] ?? []).map((v) => [v, 0]));
	for (const r of applyFacets(rows, facets, sel, facet.key))
		for (const v of new Set(facet.values(r))) if (v) counts.set(v, (counts.get(v) ?? 0) + 1);
	return [...counts].map(([value, count]) => ({ value, count })).sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
}

export const textMatch = (q: string, ...fields: (string | null | undefined)[]) => {
	const needle = q.trim().toLowerCase();
	return !needle || fields.some((s) => s?.toLowerCase().includes(needle));
};

/** Sort with blanks last whatever the direction; ties keep their incoming order. */
export function sortRows<T>(rows: T[], value: (row: T) => string | number | null, asc: boolean): T[] {
	const dir = asc ? 1 : -1;
	return [...rows].sort((a, b) => {
		const x = value(a), y = value(b);
		if (x === y) return 0;
		if (x === null || x === '') return 1;
		if (y === null || y === '') return -1;
		return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir;
	});
}
