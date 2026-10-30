/** App settings (edited on /settings), loaded once by the root layout and shared by every page. */
import type { Basemap } from './basemap.ts';

export interface StorageGroup {
	name: string;
	prefix: string;
	capacity: number | null;
}

export interface AppSettings {
	/** the main currency: totals and values are in it */
	currency: string;
	/** how much of the main currency one unit of each currency is worth */
	exchange_rates: Record<string, number>;
	local_label: string;
	non_local_keywords: string[];
	storage_groups: StorageGroup[];
	other_group: string;
	/** app bottles whose location contains this are reconciled with the Bordeaux Index portfolio */
	bi_location: string;
	map_default_basemap: Basemap;
	/** lists sort and rank wines by this critic's score */
	preferred_critic: string;
	/** a vendor's buyer's premium in percent (iDealwine 22): the bottle form offers to add it to the price */
	vendor_premiums: Record<string, number>;
}

// Mirrors the API defaults, so pages render sensibly even before (or without) the settings request
export const appSettings = $state<AppSettings>({
	currency: 'EUR',
	exchange_rates: { EUR: 1, USD: 0.92, GBP: 1.17, CHF: 1.05 },
	local_label: 'Local',
	non_local_keywords: [],
	storage_groups: [],
	other_group: 'Cellar',
	bi_location: '',
	map_default_basemap: 'plain',
	preferred_critic: '',
	vendor_premiums: {}
});

export function setSettings(next: AppSettings) {
	Object.assign(appSettings, next);
}

/** An optional connection (GET /api/integrations): Bordeaux Index, WineLabs, the LWIN list */
export interface Integration {
	id: string;
	name: string;
	configured: boolean;
	what: string;
	needs: string;
}
export interface PluginInfo {
	name: string;
	ok: boolean;
	error: string | null;
}
/** The installed map outlines' sources, with their licence and credit (the map data pack) */
export interface MapCredit {
	source: string;
	rows: number | null;
	licence: string;
	credit: string | null;
	url: string | null;
}
export const integrations = $state<{ list: Integration[]; plugins: PluginInfo[]; mapCredits: MapCredit[] }>({
	list: [],
	plugins: [],
	mapCredits: []
});
/** Whether an integration is set up (its parts of the pages show only then) */
export const configured = (id: string) => integrations.list.some((i) => i.id === id && i.configured);

export async function loadSettings(fetch: typeof globalThis.fetch) {
	try {
		const [res, ints] = await Promise.all([fetch('/api/settings'), fetch('/api/integrations')]);
		if (res.ok) setSettings(await res.json());
		if (ints.ok) {
			const body = await ints.json();
			integrations.list = body.integrations;
			integrations.plugins = body.plugins;
			integrations.mapCredits = body.map_credits ?? [];
		}
	} catch {
		// keep the defaults: a settings hiccup shouldn't take the whole app down
	}
}

/** Storage group names in display order, then the catch-all group. */
export const groupOrder = () => [...appSettings.storage_groups.map((g) => g.name), appSettings.other_group];
