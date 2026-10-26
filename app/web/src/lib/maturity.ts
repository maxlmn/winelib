/** Where a wine stands in its drinking window (set on the wine, or from a critic plug-in; see cellar.maturity in the API). */
export type Maturity = 'young' | 'ready' | 'past' | null;

export const MATURITY_LABEL: Record<NonNullable<Maturity>, string> = {
	young: 'Too young',
	ready: 'Ready',
	past: 'Past its window'
};

/** "2024–2040", "from 2026", "until 2030", or '' */
export function windowLabel(from: number | null | undefined, to: number | null | undefined) {
	if (from && to) return `${from}–${to}`;
	if (from) return `from ${from}`;
	if (to) return `until ${to}`;
	return '';
}
