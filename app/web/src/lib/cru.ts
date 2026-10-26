/** Map shades by cru (the API's `cru`: 2 grand cru, 1 premier cru, 0 otherwise): one notch darker per level. */
const NOTCH = 0.12; // of HSL lightness

type Hsl = [number, number, number];

function toHsl(hex: string): Hsl | null {
	const m = /^#?([0-9a-f]{6})$/i.exec(hex);
	if (!m) return null;
	const n = parseInt(m[1], 16);
	const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
	const max = Math.max(r, g, b), min = Math.min(r, g, b);
	let h = 0, s = 0;
	const l = (max + min) / 2;
	if (max !== min) {
		const d = max - min;
		s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
		h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
		h /= 6;
	}
	return [h, s, l];
}

function toHex([h, s, l]: Hsl): string {
	const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
	const p = 2 * l - q;
	const channel = (t: number) => {
		t = (t + 1) % 1;
		const v = t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
		return Math.round(v * 255).toString(16).padStart(2, '0');
	};
	return `#${channel(h + 1 / 3)}${channel(h)}${channel(h - 1 / 3)}`;
}

export function darken(hex: string, notches: number): string {
	const hsl = toHsl(hex);
	if (!hsl || !notches) return hex;
	return toHex([hsl[0], hsl[1], Math.max(0, hsl[2] - NOTCH * notches)]);
}

/** The same color at this lightness (0-1): a palette whose shades differ by hue only, so darkness means cru alone. */
export function atLightness(hex: string, lightness: number): string {
	const hsl = toHsl(hex);
	return hsl ? toHex([hsl[0], hsl[1], lightness]) : hex;
}

export const cruShade = (hex: string, cru: number | undefined | null) => darken(hex, cru ?? 0);
