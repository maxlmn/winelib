import type { Geometry } from 'geojson';

export type Extent = [number, number, number, number];

/** [west, south, east, north] of some GeoJSON geometries, or null if there are none. */
export function bbox(geoms: Geometry[]): Extent | null {
	let [x0, y0, x1, y1] = [Infinity, Infinity, -Infinity, -Infinity];
	const walk = (c: unknown): void => {
		if (typeof (c as number[])[0] === 'number') {
			const [x, y] = c as number[];
			[x0, y0, x1, y1] = [Math.min(x0, x), Math.min(y0, y), Math.max(x1, x), Math.max(y1, y)];
		} else (c as unknown[]).forEach(walk);
	};
	for (const g of geoms) if ('coordinates' in g) walk(g.coordinates);
	return x0 === Infinity ? null : [x0, y0, x1, y1];
}
