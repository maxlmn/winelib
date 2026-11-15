/** A wine's label in a small card by the pointer (LabelTip, in the layout): over a line's bottle ends (its pips) in
 * the cellar's, the tastings' and the home page's lists, when the wine has an uploaded label (use:labelTip on them) */
import { photoSrc } from '#lib/api/photos.ts';
import { appSettings } from '#lib/settings.svelte.ts';

let tip = $state<{ src: string; x: number; y: number; below: boolean } | null>(null);

export const labelTipState = {
	get tip() {
		return tip;
	}
};

const small = (url: string) => (/\.svg(\?|$)/i.test(url) ? url : photoSrc(url, 'thumb'));

/** On the element of a line's pips: hovered (a mouse), the wine's label shows beside it; nothing without one */
export function labelTip(node: HTMLElement, label: { url: string } | null | undefined) {
	let current = label;
	function enter(e: PointerEvent) {
		if (e.pointerType !== 'mouse' || !current || appSettings.wine_labels === 'off') return;
		const r = node.getBoundingClientRect();
		// under the pips near the top of the window, over them elsewhere; kept inside the window at its edges
		const below = r.top < 180;
		const x = Math.min(Math.max(r.left + r.width / 2, 110), innerWidth - 110);
		tip = { src: small(current.url), x, y: below ? r.bottom : r.top, below };
	}
	function leave() {
		tip = null;
	}
	node.addEventListener('pointerenter', enter);
	node.addEventListener('pointerleave', leave);
	return {
		update(next: { url: string } | null | undefined) {
			current = next;
		},
		destroy() {
			node.removeEventListener('pointerenter', enter);
			node.removeEventListener('pointerleave', leave);
			tip = null;
		}
	};
}
