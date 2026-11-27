<script lang="ts">
	/** The home page's map: the regions you drink from or keep bottles of, in their colours; a click opens its card (and a link to its page).
	 * Opened on `focus` (the latest tasting's wine) when there's one: its vineyard, else its appellation (drawn), else its
	 * region with its neighbours; else on where most of your wine comes from. */
	import { onMount } from 'svelte';
	import { portal } from '#lib/portal.ts';
	import WineMap from '#lib/components/WineMap.svelte';
	import type { Layers } from '#lib/components/WineMap.svelte';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { bbox } from '#lib/geo.ts';
	import type { Extent } from '#lib/geo.ts';
	import type { MapCollection, RegionCollection, RegionProps } from '#lib/types.ts';

	/** a wine (its vineyard, appellation or region), an evening's wines (`wineIds`, the last one last: framed together
	 * when they lie close, else the last alone), a producer (where its wines come from: their appellations and
	 * vineyards, else its region), or a place ([lng, lat]: a restaurant, a home, pinned) */
	type Focus =
		| { wineId: number | null; region: string | null; wineIds?: number[]; producerId?: undefined; point?: undefined }
		| { producerId: number; region: string | null; wineId?: undefined; wineIds?: undefined; point?: undefined }
		| { point: [number, number]; wineId?: undefined; wineIds?: undefined; producerId?: undefined; region?: undefined };
	/** full: the whole window behind the page (html.map-full in app.css), the page's cards over its left side (over
	 * its lower half on a phone) */
	/** by: what colours the regions, deeper where there's more of it: your bottles, your tastings, or both (the page's
	 * own: the cellar's bottles, the tastings' tastings) */
	let {
		minHeight = 440,
		focus = null,
		full = false,
		by = 'both',
		counts = null,
		caption = null,
		column = 540,
		framed = $bindable(null)
	}: {
		minHeight?: number;
		focus?: Focus | null;
		full?: boolean;
		by?: By;
		/** what colours the regions instead of your bottles and tastings (a list's entries, by region name) */
		counts?: Record<string, number> | null;
		/** what the map shows, in a label over it ("Last opened · ...") */
		caption?: string | null;
		/** full: the page's column width over the map's left side (app.css: html.map-full main) */
		column?: number;
		/** an evening's wines the map frames (all of them, or the last alone when they lie far apart), once known */
		framed?: number[] | null;
	} = $props();

	type By = 'both' | 'cellar' | 'tasted';

	$effect(() => {
		const root = document.documentElement;
		root.classList.toggle('map-full', full);
		root.style.setProperty('--map-column', `${column}px`);
		return () => {
			root.classList.remove('map-full');
			root.style.removeProperty('--map-column');
		};
	});
	const padColumn = $derived(column + 20);
	let winWidth = $state(1024);
	let winHeight = $state(768);
	const phone = $derived(winWidth <= 760);

	// The focused wine's vineyard and appellation (its page's shapes), kept by wine: a wine hovered again isn't asked
	// again, and the map keeps the last one shown while the next is asked (it flies there once it has it)
	type Place = { id: string | null; appellations?: MapCollection; vineyards?: MapCollection };
	type Shapes = Omit<Place, 'id'>;
	const asked = new Map<string, Promise<Shapes>>(); // by address
	let place = $state<Place | null>(null);
	// the focus as a key ("w12": a wine, "p3": a producer) and the address of its shapes
	const evening = $derived(focus?.wineIds && focus.wineIds.length > 1 ? focus.wineIds : null);
	const focusKey = $derived(
		evening ? `e${evening.join(',')}` : focus?.wineId ? `w${focus.wineId}` : focus?.producerId ? `p${focus.producerId}` : null
	);
	const shapesOf = (url: string) =>
		(asked.has(url) ? asked : asked.set(url, fetch(url).then((r) => (r.ok ? (r.json() as Promise<Shapes>) : {})).catch(() => ({})))).get(url)!;
	// An evening: its wines' shapes together when they lie within ~1° of the last one's (a Burgundy dinner), else
	// the last one's alone (Champagne and Nuits-Saint-Georges: two specks on a map of France)
	const NEAR = 1.2;
	function together(all: Shapes[], ids: number[]): Shapes & { wines: number[] } {
		const own = (p: Shapes) => (p.vineyards?.features.length ? p.vineyards : p.appellations)?.features ?? [];
		const last = all.at(-1) ?? {};
		const lastBox = own(last).length ? bbox(own(last).map((f) => f.geometry)) : null;
		if (!lastBox) return { ...last, wines: ids.slice(-1) };
		const near = all.filter((p) => {
			if (!own(p).length) return false;
			const box = bbox([...own(p), ...own(last)].map((f) => f.geometry));
			return !!box && box[2] - box[0] <= NEAR && box[3] - box[1] <= NEAR;
		});
		const merge = (k: 'vineyards' | 'appellations') => {
			const seen = new Set<unknown>();
			const features = near.flatMap((p) => p[k]?.features ?? []).filter((f) => {
				const id = `${f.properties.kind}:${f.properties.id}`;
				return !seen.has(id) && !!seen.add(id);
			});
			return features.length ? ({ type: 'FeatureCollection', features } as MapCollection) : undefined;
		};
		const wines = ids.filter((_, i) => near.includes(all[i]));
		// vineyards for all, or for none: a wine known only by its appellation would otherwise be left out unframed
		return near.every((p) => p.vineyards?.features.length)
			? { vineyards: merge('vineyards'), appellations: merge('appellations'), wines }
			: { appellations: merge('appellations'), wines };
	}
	$effect(() => {
		const key = focusKey;
		if (!key) {
			place = { id: null };
			return;
		}
		let stale = false;
		const ids = key[0] === 'e' ? key.slice(1).split(',').map(Number) : [];
		const got: Promise<Shapes & { wines?: number[] }> =
			key[0] === 'e'
				? Promise.all(ids.map((id) => shapesOf(`/api/wines/${id}/shapes`))).then((all) => together(all, ids))
				: shapesOf(key[0] === 'w' ? `/api/wines/${key.slice(1)}/shapes` : `/api/producers/${key.slice(1)}/shapes`);
		got.then((p) => {
			if (stale) return;
			place = { appellations: p.appellations, vineyards: p.vineyards, id: key };
			if (p.wines) framed = p.wines;
		});
		return () => (stale = true);
	});
	// the focus's region, as it was when its shapes came (a region-only wine)
	let placeRegion = $state<string | null>(null);
	$effect(() => {
		if (place && place.id === focusKey) placeRegion = focus?.region ?? null;
	});
	const ofProducer = $derived(place?.id?.[0] === 'p');
	const point = $derived(focus?.point ?? null);
	const vines = $derived(!point && place?.vineyards?.features.length ? place.vineyards : null);
	const apps = $derived(!point && place?.appellations?.features.length ? place.appellations : null);
	// on a vineyard: it alone filled, its appellation an outline around it
	const layers = $derived<Layers>({ appellation: vines && place?.id?.[0] !== 'p' ? 'outline' : 'fill', vineyard: 'fill', lieu: 'outline' });
	// at least `min` degrees across, centred on the box: a speck of a vineyard still shows its slope
	const atLeast = ([w, s, e, n]: Extent, min: number): Extent => {
		const cx = (w + e) / 2, cy = (s + n) / 2;
		const half = Math.max(e - w, n - s, min) / 2;
		return [cx - half, Math.max(cy - half, -85), cx + half, Math.min(cy + half, 85)];
	};

	let overview = $state<RegionCollection | null>(null);
	let failed = $state(false);
	async function load() {
		failed = false;
		try {
			const r = await fetch('/api/map/overview');
			if (!r.ok) throw new Error(String(r.status));
			overview = await r.json();
		} catch {
			failed = true; // it stayed on "Loading the map…" for good
		}
	}
	onMount(load);

	// The regions with something of the page's kind, each with its depth: its share of the most any region has (eased a
	// little, so a region with a few bottles still shows beside the one with hundreds)
	const amount = (p: RegionProps) =>
		counts ? (counts[p.name] ?? 0) : by === 'cellar' ? p.bottles : by === 'tasted' ? p.tastings : p.bottles + p.tastings;
	const regions = $derived.by(() => {
		if (!overview) return null;
		const mine = overview.features.filter((f) => amount(f.properties) > 0);
		const most = Math.max(1, ...mine.map((f) => amount(f.properties)));
		return {
			...overview,
			features: mine.map((f) => ({ ...f, properties: { ...f.properties, weight: (amount(f.properties) / most) ** 0.8 } }))
		};
	});
	// Fitted to the regions most of your bottles and tastings come from (90%), not every one: a single wine from Canada
	// or China would widen it to the whole world; the whole map without any
	const extent = $derived.by((): Extent | null => {
		// a place: its streets around it (a few km across)
		if (point) return atLeast([point[0], point[1], point[0], point[1]], 0.04);
		// the latest tasting's wine: its vineyard, else its appellation, else its region with its neighbours (~6° across)
		// (a producer: every appellation and vineyard of its wines, together)
		const own = ofProducer ? [...(apps?.features ?? []), ...(vines?.features ?? [])] : (vines ?? apps)?.features;
		const ownBox = own?.length ? bbox(own.map((f) => f.geometry)) : null;
		if (ownBox) return atLeast(ownBox, vines && !ofProducer ? 0.015 : 0.08);
		const focused = placeRegion ? regions?.features.find((f) => f.properties.name === placeRegion)?.properties.bbox : null;
		if (focused) return atLeast(focused, 6);
		const weight = (p: RegionProps) => p.bottles + p.tastings;
		const ranked = (regions?.features ?? []).map((f) => f.properties).sort((a, b) => weight(b) - weight(a));
		const total = ranked.reduce((n, p) => n + weight(p), 0);
		const main: RegionProps[] = [];
		let covered = 0;
		for (const p of ranked) {
			if (covered >= 0.9 * total) break;
			main.push(p);
			covered += weight(p);
		}
		const boxes = main.map((p) => p.bbox).filter((b) => b !== null);
		if (!boxes.length) return overview?.extent ?? null;
		return [Math.min(...boxes.map((b) => b[0])), Math.min(...boxes.map((b) => b[1])), Math.max(...boxes.map((b) => b[2])), Math.max(...boxes.map((b) => b[3]))];
	});
</script>

<svelte:window bind:innerWidth={winWidth} bind:innerHeight={winHeight} />

<div class="home-map" class:full style:min-height={full ? null : `${minHeight}px`} use:portal={full} role="region" aria-label="Your wine map">
	{#if regions && place}
		<WineMap
			{regions}
			regionHref={(r: RegionProps) => links.region(r.name)}
			appellations={apps}
			vineyards={vines}
			{layers}
			selected={null}
			basemap={appSettings.map_default_basemap}
			fitKey={point ? `place:${point.join(',')}` : `home:${place.id ?? ''}`}
			pin={point}
			flyMs={900}
			{extent}
			onselect={() => {}}
			worldCopies={false}
			cardSide={full && !phone ? 'right' : 'left'}
			padLeft={full && !phone ? padColumn : 0}
			padBottom={full && phone ? Math.round(winHeight * 0.45) : 0}
		/>
		{#if caption}<div class="caption" style:left={full && !phone ? `${padColumn}px` : null}>{caption}</div>{/if}
	{:else if failed}
		<div class="loading muted">The map couldn’t be loaded. <button type="button" class="link" onclick={load}>Try again</button></div>
	{:else}
		<div class="loading muted">Loading the map…</div>
	{/if}
</div>

<style>
	/* Full size: behind the page's column, beside the sidebar; under the bar and over the tab bar on a phone */
	.home-map.full {
		position: fixed;
		inset: 0 0 0 200px;
		z-index: 40;
		min-height: 0;
		border-radius: 0;
		background: var(--bg);
	}
	/* its scale beside the page's column, not under it */
	.home-map.full :global(.maplibregl-ctrl-bottom-left) {
		left: calc(var(--map-column, 540px) + 20px);
	}
	/* what the map shows, at its top left beside the page's column */
	.caption {
		position: absolute;
		top: 12px;
		left: 12px;
		z-index: 2;
		max-width: min(420px, calc(100% - 90px));
		padding: 5px 10px;
		font-size: 12px;
		line-height: 1.4;
		color: var(--text);
		background: color-mix(in srgb, var(--surface) 92%, transparent);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow);
		pointer-events: none;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	@media (max-width: 760px) {
		.home-map.full {
			inset: var(--nav-h, 52px) 0 var(--tab-h, 0px) 0;
		}
		/* a phone: the credits and scale just above the cards */
		.home-map.full :global(:is(.maplibregl-ctrl-bottom-left, .maplibregl-ctrl-bottom-right)) {
			left: auto;
			bottom: 45dvh;
		}
		.home-map.full :global(.maplibregl-ctrl-bottom-left) {
			left: 0;
		}
	}
	.home-map {
		position: relative;
		flex: 1;
		border-radius: calc(var(--radius) - 2px);
		overflow: hidden;
	}
	.link {
		background: none;
		border: 0;
		padding: 0 0 0 6px;
		color: var(--accent);
		cursor: pointer;
		font: inherit;
	}
	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		font-size: 13px;
	}
</style>
