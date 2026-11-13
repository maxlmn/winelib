// WineLib's mark (a wine glass in a map pin) and every file drawn from it, so they can't drift apart: the app's
// favicon and install icons (static/), the website's logo, favicon and touch icon (../../site/). The sidebar's mark
// is the same drawing in lib/components/Logo.svelte, in the palette's own colours.
//   node scripts/brand.mjs        (after changing the drawing or the colours: then commit what it wrote)
import { chromium } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const web = join(dirname(fileURLToPath(import.meta.url)), '..');
const site = join(web, '..', '..', 'site');

// The app's default palette (app.css: bordeaux): the wine, the glass on it, the night ground
const WINE = '#8e2443';
const WINE_DARK = '#d4637f';
const PAPER = '#ffffff';
const NIGHT = '#141216';

// On a 64 grid: the pin, the glass's bowl, the wine in it, its stem and foot
export const PIN = 'M32 3a21 21 0 0 1 21 21c0 15-21 37-21 37S11 39 11 24A21 21 0 0 1 32 3z';
export const BOWL = 'M24 13h16c0 9-2.6 13.6-8 14.3-5.4-.7-8-5.3-8-14.3z';
export const POUR = 'M24.6 19h14.8c-.7 5-3.2 7.6-7.4 8.2-4.2-.6-6.7-3.2-7.4-8.2z';
export const STEM = 'M32 27.3V35M27.5 36h9';

/** The mark: the pin in `pin`, the glass in `glass` (the ground it stands on) */
function mark(pin, glass, extra = '') {
	return `<path d="${PIN}" fill="${pin}"${extra}/>` +
		`<path d="${BOWL}" fill="none" stroke="${glass}" stroke-width="2.6" stroke-linejoin="round"/>` +
		`<path d="${POUR}" fill="${glass}"/>` +
		`<path d="${STEM}" fill="none" stroke="${glass}" stroke-width="2.6" stroke-linecap="round"/>`;
}
const svg = (body, view = '0 0 64 64') => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${view}">${body}</svg>\n`;

// A favicon in either theme: the browser's own scheme picks the colours
const favicon = svg(
	`<style>.p{fill:${WINE}}.g{stroke:#fff;fill:none}.w{fill:#fff}` +
		`@media (prefers-color-scheme:dark){.p{fill:${WINE_DARK}}.g{stroke:${NIGHT}}.w{fill:${NIGHT}}}</style>` +
		`<path class="p" d="${PIN}"/><path class="g" d="${BOWL}" stroke-width="2.6" stroke-linejoin="round"/>` +
		`<path class="w" d="${POUR}"/><path class="g" d="${STEM}" stroke-width="2.6" stroke-linecap="round"/>`
);
writeFileSync(join(web, 'static', 'favicon.svg'), favicon);
writeFileSync(join(site, 'public', 'favicon.svg'), favicon);
// The website's logo, beside its name: on the page's own ground, light and dark
writeFileSync(join(site, 'src', 'assets', 'logo-light.svg'), svg(mark(WINE, '#fff')));
writeFileSync(join(site, 'src', 'assets', 'logo-dark.svg'), svg(mark(WINE_DARK, NIGHT)));

// Install icons: the white pin on a wine tile. A maskable icon keeps the mark inside the middle 80% (the safe zone a
// phone's mask may crop to); the others fill more of the tile.
const tile = (scale) => {
	const t = (64 - 64 * scale) / 2;
	return svg(`<rect width="64" height="64" fill="${WINE}"/><g transform="translate(${t} ${t + 64 * scale * 0.02}) scale(${scale})">${mark(PAPER, WINE)}</g>`);
};
const PNGS = [
	[join(web, 'static', 'icon-192.png'), 192, tile(0.72)],
	[join(web, 'static', 'icon-512.png'), 512, tile(0.72)],
	[join(web, 'static', 'icon-maskable-512.png'), 512, tile(0.56)],
	[join(web, 'static', 'apple-touch-icon.png'), 180, tile(0.68)],
	[join(site, 'public', 'apple-touch-icon.png'), 180, tile(0.68)]
];
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH }); // CHROMIUM_PATH: a browser of your own
const page = await browser.newPage();
for (const [path, size, body] of PNGS) {
	await page.setViewportSize({ width: size, height: size });
	await page.setContent(`<html><body style="margin:0">${body.replace('<svg ', `<svg width="${size}" height="${size}" `)}</body></html>`);
	await page.screenshot({ path, omitBackground: false, clip: { x: 0, y: 0, width: size, height: size } });
}
await browser.close();
console.log(`favicon.svg, the website's logos and ${PNGS.length} icons written`);
