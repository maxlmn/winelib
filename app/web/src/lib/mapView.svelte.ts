/** The detail pages' maps full size (the page a column of cards over it; a sheet on a phone): `always` is the choice in Settings ›
 * Appearance (this device, remembered); `full` is the map shown now, set to `always` on each page and toggled there
 * (⤢ Full map, Back to the page). */
const KEY = 'winelib-full-map';

// Full size unless chosen otherwise (Settings › Appearance › Maps: In the page)
function load() {
	try {
		return localStorage.getItem(KEY) !== '0';
	} catch {
		return true;
	}
}

let always = $state(typeof localStorage !== 'undefined' ? load() : true);
let full = $state(always);

export const mapView = {
	get always() {
		return always;
	},
	set always(v: boolean) {
		always = v;
		full = v;
		try {
			localStorage.setItem(KEY, v ? '1' : '0');
		} catch {
			/* not remembered */
		}
	},
	get full() {
		return full;
	},
	set full(v: boolean) {
		full = v;
	}
};
