/** Vineyard picker: sub-region > village > vineyard, from the fields the vineyards table already has. */

export interface VineyardRow {
	id: number;
	name: string;
	subregion: string | null;
	village: string | null;
	bottles: number;
	tastings?: number;
}

export interface VillageNode {
	key: string;
	name: string | null;
	rows: VineyardRow[];
}

export interface SubregionNode {
	key: string;
	name: string | null;
	villages: VillageNode[];
	rows: VineyardRow[];
}

const byName = (a: string | null, b: string | null) =>
	a === null ? 1 : b === null ? -1 : a.localeCompare(b);

export function buildTree(rows: VineyardRow[]): SubregionNode[] {
	const subs = new Map<string | null, Map<string | null, VineyardRow[]>>();
	for (const r of rows) {
		const villages = subs.get(r.subregion) ?? new Map();
		villages.set(r.village, [...(villages.get(r.village) ?? []), r]);
		subs.set(r.subregion, villages);
	}
	return [...subs]
		.sort(([a], [b]) => byName(a, b))
		.map(([sub, villages]) => {
			const vs = [...villages]
				.sort(([a], [b]) => byName(a, b))
				.map(([village, rs]) => ({
					key: `v:${sub ?? ''}|${village ?? ''}`,
					name: village,
					rows: rs.sort((a, b) => a.name.localeCompare(b.name))
				}));
			return { key: `s:${sub ?? ''}`, name: sub, villages: vs, rows: vs.flatMap((v) => v.rows) };
		});
}

/** Picked ids as compact URL keys: a whole sub-region or village is one key, else one key per vineyard. */
export function encodePicks(picked: Set<number>, tree: SubregionNode[]): string[] {
	const keys: string[] = [];
	for (const s of tree) {
		if (s.name !== null && s.rows.every((r) => picked.has(r.id))) {
			keys.push(s.key);
			continue;
		}
		for (const v of s.villages) {
			if (v.name !== null && v.rows.every((r) => picked.has(r.id))) keys.push(v.key);
			else keys.push(...v.rows.filter((r) => picked.has(r.id)).map((r) => `y:${r.id}`));
		}
	}
	return keys;
}

export function decodePicks(keys: string[], tree: SubregionNode[]): Set<number> {
	const wanted = new Set(keys);
	const ids = new Set<number>();
	for (const s of tree) {
		for (const v of s.villages) {
			const all = wanted.has(s.key) || wanted.has(v.key);
			for (const r of v.rows) if (all || wanted.has(`y:${r.id}`)) ids.add(r.id);
		}
	}
	return ids;
}
