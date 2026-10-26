/** Small display helpers shared by the detail pages. */

export { stars } from '#lib/format.ts';

const longDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

/** "2024-03-09" -> "9 Mar 2024" */
export const fmtDate = (iso: string | null) => (iso ? longDate.format(new Date(`${iso}T00:00:00`)) : 'Undated');

/** A comma-separated text field as a clean list */
export const splitList = (text: string | null | undefined) =>
	(text ?? '')
		.split(/[,;]/)
		.map((s) => s.trim())
		.filter(Boolean);
