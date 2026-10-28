/** Moves an element to the end of the page's body while `on` (a full-size map: under the page's column, not inside
 * it), back to its place when not: the same element, so what it holds (a map, its zoom) carries on as it is */
export function portal(node: HTMLElement, on = true) {
	const anchor = document.createComment('portal');
	node.before(anchor);
	const place = (to: boolean) => (to ? document.body.appendChild(node) : anchor.after(node));
	place(on);
	return {
		update(to: boolean) {
			place(to);
		},
		destroy() {
			node.remove();
			anchor.remove();
		}
	};
}
