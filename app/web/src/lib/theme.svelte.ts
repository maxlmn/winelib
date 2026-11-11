/** Appearance: light/dark mode, accent palette and heading font. A per-device preference (localStorage),
 * applied to <html> as data-theme / data-font / data-palette (for a palette with its own neutrals in app.css) and
 * the --accent-light / --accent-dark / --link-mix variables.
 * app.html applies the saved values before the first paint, so there's no flash of the wrong theme. */

export type Mode = 'auto' | 'light' | 'dark';
export type Font = 'sans' | 'serif';

/** link: how much of the accent the content links take (the rest is the text color); 100% unless set */
export const PALETTES: Record<string, { name: string; light: string; dark: string; link?: string }> = {
	rose: { name: 'Rosé', light: '#c27ba0', dark: '#d690b5', link: '70%' },
	bordeaux: { name: 'Bordeaux', light: '#8e2443', dark: '#d4637f' },
	champagne: { name: 'Champagne', light: '#a67c1f', dark: '#d9b45e', link: '75%' },
	vineyard: { name: 'Vineyard', light: '#4f7a3a', dark: '#8cc06a' },
	slate: { name: 'Slate', light: '#4a6a8c', dark: '#8eb2d6' },
	pinot: { name: 'Pinot', light: '#8a4f6e', dark: '#c993b1', link: '55%' },
	graphite: { name: 'Graphite', light: '#5d6470', dark: '#aab3c0', link: '60%' },
	obsidian: { name: 'Obsidian', light: '#705dcf', dark: '#9d8cf2', link: '65%' },
	minimal: { name: 'Minimal', light: '#6a8695', dark: '#889eaa', link: '75%' }
};
export type Palette = string;

const KEY = 'winelib-theme';

/** The text on a fill of this colour: white, or near-black on a light one (whichever reads better; the same sum in
 * app.html, before the first paint) */
export function onColor(hex: string) {
	const [r, g, b] = [1, 3, 5].map((i) => {
		const c = parseInt(hex.slice(i, i + 2), 16) / 255;
		return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
	});
	const l = 0.2126 * r + 0.7152 * g + 0.0722 * b;
	return 1.05 / (l + 0.05) >= (l + 0.05) / 0.06 ? '#fff' : '#1a171c';
}

export const theme = $state({ mode: 'auto' as Mode, palette: 'bordeaux' as Palette, font: 'serif' as Font, dark: false });

const media = () => matchMedia('(prefers-color-scheme: dark)');

function apply() {
	theme.dark = theme.mode === 'dark' || (theme.mode === 'auto' && media().matches);
	const root = document.documentElement;
	const p = PALETTES[theme.palette];
	root.dataset.theme = theme.dark ? 'dark' : 'light';
	root.dataset.font = theme.font;
	root.dataset.palette = theme.palette;
	root.style.setProperty('--accent-light', p.light);
	root.style.setProperty('--accent-dark', p.dark);
	root.style.setProperty('--link-mix', p.link ?? '100%');
	root.style.setProperty('--on-accent', onColor(theme.dark ? p.dark : p.light));
}

export function initTheme() {
	try {
		const saved = JSON.parse(localStorage.getItem(KEY) ?? '{}');
		if (saved.mode in { auto: 1, light: 1, dark: 1 }) theme.mode = saved.mode;
		if (saved.palette in PALETTES) theme.palette = saved.palette;
		if (saved.font === 'serif' || saved.font === 'sans') theme.font = saved.font;
	} catch {
		// private mode or corrupt value: keep the defaults
	}
	apply();
	media().addEventListener('change', () => theme.mode === 'auto' && apply());
}

export function setTheme(patch: Partial<Pick<typeof theme, 'mode' | 'palette' | 'font'>>) {
	Object.assign(theme, patch);
	apply();
	try {
		const p = PALETTES[theme.palette];
		localStorage.setItem(KEY, JSON.stringify({ mode: theme.mode, palette: theme.palette, font: theme.font, light: p.light, dark: p.dark, link: p.link }));
	} catch {
		// not persisted, still applied for this visit
	}
}

/** The current accent as a hex color, for canvas/map paint that can't read CSS variables. */
export const accentColor = () => PALETTES[theme.palette][theme.dark ? 'dark' : 'light'];
