/** Moves an element to the end of the page's body (a full-size map: under the page's column, not inside it) */
export function portal(node: HTMLElement) {
	document.body.appendChild(node);
	return {
		destroy() {
			node.remove();
		}
	};
}
