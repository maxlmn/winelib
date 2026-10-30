/** Every page's URL in one place, so pages link to each other the same way. */

type Id = number | string;
type Query = Record<string, string | number | null | undefined>;

function withQuery(path: string, query?: Query) {
	const p = new URLSearchParams();
	for (const [k, v] of Object.entries(query ?? {})) if (v !== null && v !== undefined && v !== '') p.set(k, String(v));
	return p.size ? `${path}?${p}` : path;
}

export const links = {
	// Lists and dashboards
	home: () => '/',
	cellar: (query?: Query) => withQuery('/cellar', query),
	/** the cellar as a printable wine list (the cellar's filters as its query) */
	wineList: () => '/cellar/list',
	lists: () => '/lists',
	list: (id: Id) => `/lists/${id}`,
	tastings: (query?: Query) => withQuery('/tastings', query),
	/** an occasion: the journal on that day at that place (a place's name or the free-text location; "Unknown" when
	 * neither), every wine poured */
	occasion: (date: string, where: string | null) =>
		withQuery('/tastings', { period: 'custom', from: date, to: date, loc: where || 'Unknown' }),
	summary: () => '/summary',
	producers: (query?: Query) => withQuery('/producers', query),
	grapes: () => '/grapes',
	vintages: () => '/vintages',
	places: (query?: Query) => withQuery('/places', query),
	map: (query?: Query) => withQuery('/map', query),
	settings: () => '/settings',
	/** Settings › Maintenance opened on one task, its preview started (a report: run) */
	maintenance: (task: string) => withQuery('/settings', { task }) + '#maintenance',
	/** where the reference data and the map come from, their licences */
	about: () => '/about',
	/** the Help guides, or one of them */
	help: (slug?: string) => (slug ? `/help/${encodeURIComponent(slug)}` : '/help'),

	// Detail pages
	producer: (id: Id) => `/producers/${id}`,
	wine: (id: Id) => `/wines/${id}`,
	bottle: (id: Id) => `/bottles/${id}`,
	tasting: (id: Id) => `/tastings/${id}`,
	place: (id: Id) => `/places/${id}`,
	appellation: (id: Id) => `/appellations/${id}`,
	/** by id or by name (most pages only know a region's name) */
	region: (idOrName: Id) => `/regions/${encodeURIComponent(String(idOrName))}`,
	grape: (idOrName: Id) => `/grapes/${encodeURIComponent(String(idOrName))}`,
	vineyard: (id: Id) => `/vineyards/${id}`,
	/** "2016" or "NV" (an NV label with its disgorgement date goes to NV) */
	vintage: (v: string) => `/vintages/${/^\d{4}$/.test(v.trim()) ? v.trim() : 'NV'}`,

	/** WineLabs' quote page for that vintage (LWIN11 = LWIN7 + vintage), or all vintages for NV */
	winelabs: (lwin: string, vintage?: string | null) =>
		`https://winelabs.ai/quote/${lwin}${vintage && /^\d{4}$/.test(vintage) ? vintage : ''}`,

	// Forms
	newProducer: () => '/producers/new',
	editProducer: (id: Id) => `/producers/${id}/edit`,
	editAppellation: (id: Id) => `/appellations/${id}/edit`,
	editVineyard: (id: Id) => `/vineyards/${id}/edit`,
	/** a vineyard drawn for a wine, then linked to it */
	newWine: (query?: { producer_id?: Id }) => withQuery('/wines/new', query),
	editWine: (id: Id) => `/wines/${id}/edit`,
	newBottle: (query?: { wine_id?: Id }) => withQuery('/bottles/new', query),
	editBottle: (id: Id) => `/bottles/${id}/edit`,
	newTasting: (query?: { wine_id?: Id; bottle_id?: Id; place_id?: Id; date?: string }) => withQuery('/tastings/new', query),
	editTasting: (id: Id) => `/tastings/${id}/edit`,
	newPlace: () => '/places/new',
	editPlace: (id: Id) => `/places/${id}/edit`,
	newVisit: (query?: { place_id?: Id }) => withQuery('/visits/new', query),
	editVisit: (id: Id) => `/visits/${id}/edit`
};
