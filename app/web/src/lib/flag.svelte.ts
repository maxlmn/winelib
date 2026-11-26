/** A per-browser on/off choice kept in localStorage (on unless turned off): the maps' Relief and Contours. Read and
 * written in try/catch: a private window, or storage blocked, keeps it for the visit only. */
export function persistedFlag(key: string) {
	let on = true;
	try {
		on = localStorage.getItem(key) !== 'off';
	} catch {
		/* storage unavailable: on */
	}
	const state = $state({ on });
	return {
		state,
		set(value: boolean) {
			state.on = value;
			try {
				localStorage.setItem(key, value ? 'on' : 'off');
			} catch {
				/* for this visit only */
			}
		}
	};
}
