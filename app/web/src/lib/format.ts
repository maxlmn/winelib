import { appSettings } from './settings.svelte.ts';

// Numbers grouped as the browser's language does
const whole = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

const SYMBOLS: Record<string, string> = { SGD: 'S$', USD: 'US$', EUR: '€', GBP: '£', AUD: 'A$', HKD: 'HK$', JPY: '¥', CHF: 'CHF ' };
/** "€", "S$", or the code and a space */
export const symbol = (currency: string) => SYMBOLS[currency] ?? `${currency} `;

/** An amount in the main currency (Settings), as every total and value is: €1,250 */
export const money = (n: number) => `${symbol(appSettings.currency)}${whole.format(n)}`;

/** An amount in the main currency shown in another, with the Settings page's rates (main currency per unit). */
export function inCurrency(n: number, currency: string, rates: Record<string, number>) {
	return `${symbol(currency)}${whole.format(n / (currency === appSettings.currency ? 1 : (rates[currency] ?? 1)))}`;
}

/** An amount in its own currency, whole units: 1,250 EUR; – when there's none. */
export const amount = (n: number | null | undefined, currency?: string | null) =>
	n == null ? '–' : `${whole.format(n)} ${currency ?? ''}`.trim();

export const gbp = (n: number | null | undefined) => (n == null ? '–' : `£${whole.format(n)}`);

export const compact = (n: number) => (n >= 1000 ? `${whole.format(n / 1000)}k` : whole.format(n));

export const pct = (from: number, to: number) => (from ? ((to - from) / from) * 100 : 0);

/** Today in the browser's own time zone, YYYY-MM-DD (toISOString's is UTC: yesterday, early in the morning in Asia) */
export const today = () => {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** One bar per bottle, its width scaled by format: 37.5cl = 2px, 75cl = 4px, magnum = 8px... */
export function barWidth(format: string | null) {
	const m = (format ?? '').toLowerCase().replace(/\s/g, '').match(/^(\d+(?:\.\d+)?)cl$/);
	return m ? Math.max(2, Math.round((parseFloat(m[1]) / 75) * 4)) : 4;
}

/** A bottle end's diameter against a 75cl bottle's, following its volume: a magnum ~1.4x, a half bottle smaller */
export const endScale = (format: string | null) => Math.min(1.6, Math.max(0.75, Math.sqrt(barWidth(format) / 4)));

/** Michelin stars: ★★ (none: empty) */
export const stars = (n: number | null | undefined) => (n ? '★'.repeat(n) : '');
