/** An image shown whole in a pop-up over the page (Lightbox, in the layout), never a page of its own: a click on a
 * label, a photo or a thumbnail opens it there (use:lightbox on its link); a click with a modifier (a new tab) still
 * opens the file */
let shown = $state<{ src: string; alt: string } | null>(null);

export const lightbox = {
	get shown() {
		return shown;
	},
	open(src: string, alt = '') {
		shown = { src, alt };
	},
	close() {
		shown = null;
	}
};

/** On an image's link: a plain click opens the image in the pop-up (the link's own href, or `src`) */
export function opensImage(node: HTMLAnchorElement, opts: { src?: string; alt?: string } = {}) {
	let current = opts;
	function click(e: MouseEvent) {
		if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
		e.preventDefault();
		lightbox.open(current.src ?? node.href, current.alt ?? node.querySelector('img')?.alt ?? '');
	}
	node.addEventListener('click', click);
	return {
		update(next: { src?: string; alt?: string } = {}) {
			current = next;
		},
		destroy() {
			node.removeEventListener('click', click);
		}
	};
}
