// Dot color per wine type
export const TYPE_COLORS: Record<string, string> = {
	Red: '#8b1a1a',
	White: '#e8c95a',
	Bubbles: '#f0dc9a',
	'Bubbles Rose': '#e8a9b8',
	Rose: '#d5a6bd',
	Sweet: '#e69138',
	Fortified: '#9487df',
	Orange: '#e69138'
};

// Regions without a colour of their own: a neutral grey
export const FALLBACK_REGION = '#9a9893';

export function rgb(hex: string): [number, number, number] {
	const h = hex.replace('#', '');
	const n = parseInt(h.length === 3 ? [...h].map((c) => c + c).join('') : h.slice(0, 6), 16);
	return Number.isNaN(n) ? [154, 152, 147] : [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const isLight = ([r, g, b]: number[]) => 0.299 * r + 0.587 * g + 0.114 * b > 150;

const toHex = (c: number[]) => '#' + c.map((x) => Math.round(x).toString(16).padStart(2, '0')).join('');

/** Heatmap ramp per region: pale tint -> the region's own color -> a deeper shade at the peak (t in 0..1). */
export function ramp(hex: string, t: number): { fill: string; dark: boolean } {
	const c = rgb(hex);
	let out: number[];
	if (t < 0.5) {
		const mix = 0.35 + 1.3 * t;
		out = c.map((x) => 255 + (x - 255) * mix);
	} else {
		const shade = (t - 0.5) * 0.9;
		out = c.map((x) => x * (1 - shade));
	}
	return { fill: toHex(out), dark: isLight(out) };
}

/** A wine type's colour (grey for none or an unknown one) */
export const typeColor = (type: string | null | undefined) => TYPE_COLORS[type ?? ''] ?? '#999';
