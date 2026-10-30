<script lang="ts">
	import { setParams } from '#lib/url.ts';
	import { messageOf, request } from '#lib/api/http.ts';
	import RegionName from '#lib/components/RegionName.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { onMount, tick, untrack } from 'svelte';
	import { page } from '$app/state';
	import VineyardTree from '#lib/components/VineyardTree.svelte';
	import WineMap from '#lib/components/WineMap.svelte';
	import type { Basemap, Layers, Selection } from '#lib/components/WineMap.svelte';
	import { DEFAULT_LAYERS } from '#lib/components/WineMap.svelte';
	import LayerToggle from '#lib/components/LayerToggle.svelte';
	import { darken } from '#lib/cru.ts';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { plural } from '#lib/format.ts';
	import { collection, loadShapes, useVersion, withoutShape } from '#lib/api/mapShapes.ts';
	import type { Extent } from '#lib/geo.ts';
	import type { Geometry } from 'geojson';
	import type { MapProps, RegionCollection, RegionProps } from '#lib/types.ts';
	import { buildTree, decodePicks, encodePicks } from '#lib/vineyards.ts';
	import type { VineyardRow } from '#lib/vineyards.ts';

	type Detail = Record<string, string | number | null | object>;
	/** A region's page: names and figures for the pickers, its outline and extent. No appellation or
	 *  vineyard geometry: shapes come only for what's picked (see lib/api/mapShapes.ts) */
	interface RegionIndex {
		version: string;
		region: { id: number; name: string; color: string };
		appellations: MapProps[];
		vineyards: MapProps[];
		outline: Geometry | null;
		extent: Extent | null;
	}
	type Only = 'all' | 'cellar' | 'tastings';

	const LIST_LIMIT = 300;
	const params = $derived(page.url.searchParams);
	/** No region: the overview, one outline per region */
	const regionName = $derived(params.get('region'));
	const only = $derived<Only>(params.get('only') === 'cellar' ? 'cellar' : params.get('only') === 'tastings' ? 'tastings' : 'all');
	const selected = $derived.by((): Selection => {
		const [kind, id] = (params.get('sel') ?? '').split(':');
		return (kind === 'appellation' || kind === 'vineyard') && id ? { kind, id: +id } : null;
	});

	let overview = $state<RegionCollection | null>(null);
	let idx = $state<RegionIndex | null>(null);
	let loading = $state(true);
	let pending = $state(0); // shape requests under way
	let shapesVersion = $state(0); // bumped when shapes arrive
	let detail = $state<Detail | null>(null);
	let basemap = $state<Basemap>(appSettings.map_default_basemap);
	// each kind filled, outlined or hidden (LayerToggle)
	let layers = $state<Layers>({ ...DEFAULT_LAYERS });
	let query = $state('');
	let tab = $state<'appellations' | 'vineyards'>('appellations');
	let mapView = $state<WineMap>();

	const allRegions = $derived((overview?.features ?? []).map((f) => f.properties));
	const region = $derived(regionName ? allRegions.find((r) => r.name === regionName) ?? null : null);

	/** The cellar / tastings filter, for regions and for the pickers alike */
	const passes = (p: { bottles: number; tastings: number }) =>
		only === 'cellar' ? p.bottles > 0 : only === 'tastings' ? p.tastings > 0 : true;
	const textMatch = (...fields: (string | null | undefined)[]) =>
		!query || fields.some((s) => s?.toLowerCase().includes(query.toLowerCase()));

	// Appellations and vineyards are picked independently; both live in the URL.
	// Vineyards as compact keys (whole sub-region / village, or single vineyards).
	const vineyardIndex = $derived((idx?.vineyards ?? []) as (MapProps & VineyardRow)[]);
	const pickedApps = $derived(new Set(params.getAll('ap').map(Number)));
	const fullTree = $derived(buildTree(vineyardIndex));
	const picked = $derived(decodePicks(params.getAll('vy'), fullTree));

	const openRegion = (name: string | null) => {
		query = '';
		setParams({ region: name, sel: null, ap: null, vy: null });
	};
	const setPicked = (ids: Set<number>) => setParams({ vy: encodePicks(ids, fullTree) });
	const setPickedApps = (ids: Set<number>) => setParams({ ap: [...ids].map(String) });
	function togglePickedApp(id: number) {
		const next = new Set(pickedApps);
		next.has(id) ? next.delete(id) : next.add(id);
		setPickedApps(next);
	}

	// what couldn't load, said in the map's status box (not a "Loading…" left up)
	let loadError = $state('');
	onMount(async () => {
		try {
			overview = await request<typeof overview>('/api/map/overview');
		} catch (e) {
			loadError = `The map couldn’t load: ${messageOf(e)}`;
		}
		if (!regionName) loading = false;
	});

	// A region's index (small; an unchanged one is a 304)
	$effect(() => {
		const r = region;
		if (!r) {
			idx = null;
			// no such region (an old link), or back to the overview: nothing more to wait for once it's there
			if (overview || loadError) loading = false;
			return;
		}
		let cancelled = false;
		loading = true;
		request<RegionIndex>(`/api/map/regions/${r.id}`)
			.then((data) => {
				if (cancelled) return;
				useVersion(data.version);
				idx = data;
			})
			.catch((e) => !cancelled && (loadError = `${r.name} couldn’t load: ${messageOf(e)}`))
			.finally(() => !cancelled && (loading = false));
		return () => (cancelled = true);
	});

	// Drawn: only the picked appellations and vineyards
	const drawAppRows = $derived((idx?.appellations ?? []).filter((a) => pickedApps.has(a.id)));
	const drawVineRows = $derived(vineyardIndex.filter((v) => picked.has(v.id)));
	const drawAppIds = $derived(drawAppRows.map((a) => a.id));
	const drawIds = $derived(drawVineRows.map((v) => v.id));
	// Shapes kept from earlier (this visit or a previous one) draw at once; the rest arrive in batches
	$effect(() => {
		const apps = drawAppIds;
		const vines = drawIds;
		if (!apps.length && !vines.length) return;
		untrack(() => pending++);
		loadShapes(apps, vines, () => shapesVersion++)
			.catch((e) => console.error(e))
			.finally(() => {
				pending--;
				shapesVersion++;
			});
	});
	const shownApps = $derived.by(() => {
		void shapesVersion;
		return drawAppRows.length ? collection('appellation', drawAppRows) : null;
	});
	const vineyards = $derived.by(() => {
		void shapesVersion;
		return drawVineRows.length ? collection('vineyard', drawVineRows) : null;
	});
	const missing = $derived.by(() => {
		void shapesVersion;
		const noApp = new Set(withoutShape('appellation', drawAppIds));
		const noVine = new Set(withoutShape('vineyard', drawIds));
		return [...drawAppRows.filter((a) => noApp.has(a.id)), ...drawVineRows.filter((v) => noVine.has(v.id))].map((p) => p.name);
	});
	const drawn = $derived((shownApps?.features.length ?? 0) + (vineyards?.features.length ?? 0));

	// Region outlines: every (filtered) region on the overview; inside a region, its own, for context
	const shownRegions = $derived.by(() => {
		if (!overview) return null;
		if (!region) return { ...overview, features: overview.features.filter((f) => passes(f.properties)) };
		const own = overview.features.find((f) => f.properties.id === region.id);
		const geometry = idx?.outline ?? own?.geometry ?? null;
		return own ? { ...overview, features: [{ ...own, geometry }] } : null;
	});
	const fitKey = $derived(region ? `region:${region.id}` : `overview:${only}`);
	const extent = $derived.by((): Extent | null => {
		if (region) return idx?.extent ?? region.bbox ?? null;
		const boxes = (shownRegions?.features ?? []).map((f) => f.properties.bbox).filter((b) => b !== null);
		if (!boxes.length) return overview?.extent ?? null;
		return [Math.min(...boxes.map((b) => b[0])), Math.min(...boxes.map((b) => b[1])), Math.max(...boxes.map((b) => b[2])), Math.max(...boxes.map((b) => b[3]))];
	});

	// Details for the selected feature
	$effect(() => {
		const sel = selected;
		detail = null;
		if (!sel) return;
		let cancelled = false;
		request<typeof detail>(`/api/${sel.kind === 'appellation' ? 'appellations' : 'vineyards'}/${sel.id}`)
			.then((d) => !cancelled && (detail = d))
			.catch(() => !cancelled && (detail = null)); // the card on the map still says what it is
		return () => (cancelled = true);
	});

	const select = (p: { kind: 'appellation' | 'vineyard' | 'region'; id: number } | null) =>
		setParams({ sel: p && p.kind !== 'region' ? `${p.kind}:${p.id}` : null });

	/** Fly to a feature once its shape is in (it may still be loading) */
	async function flyTo(sel: NonNullable<Selection>) {
		await loadShapes(sel.kind === 'appellation' ? [sel.id] : [], sel.kind === 'vineyard' ? [sel.id] : []);
		shapesVersion++;
		await tick();
		mapView?.focus(sel);
	}

	function focusAppellation(p: MapProps) {
		// Picking an appellation by name also draws it
		if (!pickedApps.has(p.id)) setParams({ ap: [...pickedApps, p.id].map(String), sel: `appellation:${p.id}` });
		else select(p);
		flyTo({ kind: 'appellation', id: p.id });
	}

	function focusVineyard(row: VineyardRow) {
		// Picking a vineyard by name also draws it
		if (!picked.has(row.id)) {
			const next = new Set(picked);
			next.add(row.id);
			setParams({ vy: encodePicks(next, fullTree), sel: `vineyard:${row.id}` });
		} else select({ kind: 'vineyard', id: row.id });
		flyTo({ kind: 'vineyard', id: row.id });
	}

	const regionList = $derived(
		allRegions
			.filter((r) => passes(r) && textMatch(r.name, r.country))
			.sort((a, b) => a.name.localeCompare(b.name))
	);
	const appList = $derived(
		(idx?.appellations ?? [])
			.filter((p) => passes(p) && textMatch(p.name, p.subregion))
			// Sorted here, not in SQL: databases order accented names (Bâtard…) after the alphabet
			.sort((a, b) => a.name.localeCompare(b.name))
	);
	const treeRows = $derived(vineyardIndex.filter((v) => passes(v) && textMatch(v.name, v.village, v.subregion)));
	// How many listed appellations aren't drawn yet
	const unpickedApps = $derived(appList.filter((p) => !pickedApps.has(p.id)).length);

	const detailTastings = $derived(((detail?.stats ?? null) as { tastings?: number } | null)?.tastings ?? 0);
	const fmtYield = (d: Detail) =>
		[d.max_yield_hl && `${d.max_yield_hl} hl/ha`, d.max_yield_kg && `${d.max_yield_kg} kg/ha`].filter(Boolean).join(' · ');
</script>

<svelte:head><title>{region ? `${regionLabel(region.name)} · ` : ''}Map · WineLib</title></svelte:head>

{#snippet badges(p: { bottles: number; tastings: number })}
	{#if p.tastings}<span class="badge tasted num" title={plural(p.tastings, 'tasting')}>✎ {p.tastings}</span>{/if}
	{#if p.bottles}<span class="badge num" title="{plural(p.bottles, 'bottle')} in cellar">{p.bottles}</span>{/if}
{/snippet}

<div class="page-head">
	<h1>
		{#if region}<button class="crumb" onclick={() => openRegion(null)}>Map</button> <span class="muted">/</span> {regionLabel(region.name)}
			<a class="region-page" href={links.region(region.name)}>Region page →</a>{:else}Map{/if}
	</h1>
	<div class="seg small">
		{#each [['plain', 'Plain'], ['satellite', 'Satellite']] as [id, label]}
			<button class:on={basemap === id} aria-pressed={basemap === id} onclick={() => (basemap = id as Basemap)}>{label}</button>
		{/each}
	</div>
</div>

<div class="layout">
	<div class="map card">
		<WineMap
			bind:this={mapView}
			regions={shownRegions}
			onregion={region ? null : (r: RegionProps) => openRegion(r.name)}
			appellations={shownApps}
			{vineyards}
			{layers}
			{selected}
			{basemap}
			{fitKey}
			{extent}
			onselect={(p: MapProps | null) => select(p)}
		/>
		{#if overview && overview.outlines === false}
			<div class="no-outlines card">
				No appellation or vineyard outlines installed yet: only regions are drawn.
				<a href={links.settings('maintenance')}>Settings › Maintenance › Map outlines</a> downloads them.
			</div>
		{/if}
		{#if loadError}<div class="loading card failed" role="alert">{loadError}</div>
		{:else if loading || pending}<div class="loading card">{loading ? 'Loading…' : `Drawing… ${drawn} of ${drawAppIds.length + drawIds.length}`}</div>{/if}
		{#if region && !loading && !drawAppIds.length && !drawIds.length}
			<div class="tip card muted">
				{idx && !idx.appellations.length && !idx.vineyards.length
					? 'No appellation or vineyard outlines here yet'
					: 'Tick appellations or vineyards to draw them'}
			</div>
		{/if}
	</div>

	<aside class="card">
		<div class="seg filter">
			{#each [['all', 'All'], ['cellar', 'My cellar'], ['tastings', 'My tastings']] as [id, label]}
				<button class:on={only === id} aria-pressed={only === id} onclick={() => setParams({ only: id === 'all' ? null : id })}>{label}</button>
			{/each}
		</div>

		{#if !region}
			<input class="search" type="search" placeholder="Search region or country…" bind:value={query} />
			<div class="list">
				{#each regionList as r (r.id)}
					<button class="row pick" onclick={() => openRegion(r.name)}>
						<span class="sw" style:background={r.color}></span>
						<span class="name">{r.name}{#if r.country && r.country !== r.name}<span class="muted">&nbsp;· {r.country}</span>{/if}</span>
						{@render badges(r)}
					</button>
				{/each}
				{#if overview && !regionList.length}
					<p class="muted hint">{only === 'cellar' ? 'No region with bottles in your cellar.' : only === 'tastings' ? 'No region with tastings.' : 'No region matches.'}</p>
				{/if}
			</div>
		{:else}
			<div class="regionbar">
				<button class="link" onclick={() => openRegion(null)}>← All regions</button>
				<select value={region.name} onchange={(e) => openRegion(e.currentTarget.value)} aria-label="Region">
					{#each allRegions.toSorted((a, b) => a.name.localeCompare(b.name)) as r (r.id)}
						<option value={r.name}>{r.name}{r.country && r.country !== r.name ? ` · ${r.country}` : ''}</option>
					{/each}
				</select>
			</div>

			<div class="toggles">
				<LayerToggle label="Appellations" bind:mode={layers.appellation} swatch={region.color ?? undefined}
					note="{drawAppIds.length} of {idx?.appellations.length ?? 0} drawn" />
				<LayerToggle label="Vineyards" bind:mode={layers.vineyard} swatch={darken(region.color ?? '#9a9893', 1)} note="{drawIds.length} of {vineyardIndex.length} drawn" />
				<LayerToggle label="Lieux-dits" bind:mode={layers.lieu} dashed note="from close zoom" />
			</div>

			<input class="search" type="search" placeholder="Search name, village or sub-region…" bind:value={query} />

			{#if selected}
				<div class="detail">
					<button class="close" onclick={() => select(null)} aria-label="Close">✕</button>
					<div class="kind">{selected.kind}</div>
					{#if detail}
						<h3>{detail.name}</h3>
						<dl>
							{#each [['Region', detail.region], ['Sub-region', detail.subregion], ['Village', detail.village], ['Type', detail.type], ['Category', detail.category], ['PDO', detail.pdo_id ? `${detail.pdo_id}${detail.registration_date ? ` (reg. ${detail.registration_date})` : ''}` : null], ['Max yield', fmtYield(detail)]] as [k, v]}
								{#if v}<dt>{k}</dt><dd>{#if k === 'Region'}<a href={links.region(String(v))}><RegionName name={String(v)} /></a>{:else}{v}{/if}</dd>{/if}
							{/each}
						</dl>
						{#if detail.varieties}
							<details><summary>Authorized varieties</summary><p>{detail.varieties}</p></details>
						{/if}
						{#if detail.details}
							<details><summary>Notes</summary><p>{detail.details}</p></details>
						{/if}
						<div class="links">
							{#if detail.bottles}
								{#if selected.kind === 'appellation'}
									<a class="owned" href={links.cellar({ view: 'cards', appellation: String(detail.name) })}>{plural(Number(detail.bottles), 'bottle')} in cellar →</a>
								{:else}
									<span class="owned">{plural(Number(detail.bottles), 'bottle')} in cellar</span>
								{/if}
							{/if}
							{#if detailTastings}
								<a class="tasted" href="{selected.kind === 'appellation' ? links.appellation(selected.id) : links.vineyard(selected.id)}">{plural(detailTastings, 'tasting')} →</a>
							{/if}
							<button class="link" onclick={() => selected && flyTo(selected)}>Zoom to</button>
							<a href={selected.kind === 'appellation' ? links.appellation(selected.id) : links.vineyard(selected.id)}>Details →</a>
						</div>
					{:else}
						<p class="muted">Loading…</p>
					{/if}
				</div>
			{/if}

			<div class="tabs">
				<button class:on={tab === 'appellations'} aria-pressed={tab === 'appellations'} onclick={() => (tab = 'appellations')}>Appellations <span class="num">{appList.length}</span></button>
				{#if vineyardIndex.length}
					<button class:on={tab === 'vineyards'} aria-pressed={tab === 'vineyards'} onclick={() => (tab = 'vineyards')}>Vineyards <span class="num">{treeRows.length}</span></button>
				{/if}
				{#if tab === 'vineyards' && picked.size}
					<button class="link clear" onclick={() => setParams({ vy: null })}>Clear {picked.size}</button>
				{:else if tab === 'appellations'}
					<!-- Show all: every appellation listed (the region's, or those the search and filter keep) drawn -->
					{#if unpickedApps}
						<button class="link clear" onclick={() => setPickedApps(new Set([...pickedApps, ...appList.map((p) => p.id)]))}>
							Show all {appList.length}
						</button>
					{/if}
					{#if pickedApps.size}<button class="link clear" onclick={() => setParams({ ap: null })}>Clear {pickedApps.size}</button>{/if}
				{/if}
			</div>

			<div class="list">
				<!-- Both lists stay mounted (hidden when inactive) so the tree keeps its expanded groups -->
				{#if vineyardIndex.length}
					<div hidden={tab !== 'vineyards'}>
						<VineyardTree
							rows={treeRows}
							{picked}
							onpick={setPicked}
							onfocus={focusVineyard}
							selectedId={selected?.kind === 'vineyard' ? selected.id : null}
							expandAll={query.length >= 2 || only !== 'all'}
						/>
						{#if !treeRows.length}<p class="muted hint">No vineyard matches.</p>{/if}
					</div>
				{/if}
				<div hidden={tab === 'vineyards' && vineyardIndex.length > 0}>
					{#each appList.slice(0, LIST_LIMIT) as p (p.id)}
						<div class="row" class:sel={selected?.kind === 'appellation' && selected?.id === p.id}>
							<input type="checkbox" checked={pickedApps.has(p.id)} onchange={() => togglePickedApp(p.id)} aria-label={`Draw ${p.name}`} />
							<button class="pick" onclick={() => focusAppellation(p)}>
								<span class="sw" style:background={p.color}></span>
								<span class="name">{p.name}</span>
								{@render badges(p)}
							</button>
						</div>
					{/each}
					{#if appList.length > LIST_LIMIT}
						<p class="muted hint">{appList.length - LIST_LIMIT} more: search to narrow down</p>
					{/if}
					{#if idx && !appList.length}<p class="muted hint">No appellation matches.</p>{/if}
				</div>
				{#if missing.length}
					<details class="missing">
						<summary class="muted">{missing.length} without boundaries</summary>
						<p class="muted">{missing.join(' · ')}</p>
					</details>
				{/if}
			</div>
		{/if}
	</aside>
</div>

<style>
	.crumb {
		border: none;
		background: none;
		padding: 0;
		font: inherit;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
		cursor: pointer;
	}
	.crumb:hover {
		color: var(--accent);
	}
	.seg.small {
		margin-left: auto;
		font-size: 13px;
	}
	.seg.filter {
		display: flex;
		font-size: 13px;
	}
	.seg.filter button {
		flex: 1;
		padding: 6px 4px;
	}
	.layout {
		display: grid;
		grid-template-columns: 1fr 340px;
		gap: 14px;
		height: calc(100vh - 120px);
		min-height: 520px;
	}
	.map {
		position: relative;
		overflow: hidden;
	}
	.loading.failed {
		color: var(--down);
	}
	.loading,
	.no-outlines {
		position: absolute;
		left: 12px;
		right: 56px;
		top: 12px;
		padding: 8px 12px;
		font-size: 13px;
		z-index: 1;
	}
	.no-outlines a {
		color: var(--accent);
	}
	.tip {
		position: absolute;
		right: 56px;
		top: 12px;
		padding: 6px 12px;
		font-size: 13px;
	}
	.tip {
		top: auto;
		right: auto;
		left: 50%;
		bottom: 24px;
		transform: translateX(-50%);
	}
	aside {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 12px;
		min-height: 0;
	}
	.regionbar {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.regionbar .link {
		white-space: nowrap;
		font-size: 13px;
	}
	select,
	.search {
		width: 100%;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
	}
	.toggles {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 4px;
		font-size: 13px;
	}
	.sw {
		width: 10px;
		height: 10px;
		border-radius: 3px;
		flex: none;
		background: #9a9893;
	}
	.detail {
		position: relative;
		padding: 12px;
		border-radius: 8px;
		background: var(--surface-2);
		font-size: 13px;
	}
	.detail h3 {
		margin: 2px 24px 8px 0;
		font-size: 15px;
	}
	.kind {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
	}
	.close {
		position: absolute;
		top: 8px;
		right: 8px;
		border: none;
		background: none;
		cursor: pointer;
		color: var(--muted);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 3px 10px;
		margin: 0;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
	}
	.detail details {
		margin-top: 8px;
	}
	.detail summary {
		cursor: pointer;
		color: var(--accent);
	}
	.detail p {
		margin: 6px 0 0;
		max-height: 140px;
		overflow-y: auto;
	}
	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		margin-top: 10px;
		align-items: center;
	}
	.links a,
	.link {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.links a:hover, .link:hover {
		color: var(--accent);
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		cursor: pointer;
	}
	.owned {
		color: var(--gold) !important;
		font-weight: 600;
	}
	.tabs {
		display: flex;
		align-items: center;
		gap: 2px;
		border-bottom: 1px solid var(--border);
	}
	.tabs button:not(.link) {
		border: none;
		background: none;
		padding: 6px 10px;
		cursor: pointer;
		color: var(--muted);
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		font-size: 13px;
	}
	.tabs button.on {
		color: var(--text);
		border-bottom-color: var(--accent);
		font-weight: 600;
	}
	.clear {
		margin-left: auto;
		font-size: 12px;
	}
	.clear + .clear {
		margin-left: 12px;
	}
	.list {
		overflow-y: auto;
		flex: 1;
		min-height: 0;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0 4px;
		border-radius: 6px;
		font-size: 13px;
	}
	.row input {
		margin: 0;
		accent-color: var(--accent);
	}
	.pick {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
		min-width: 0;
		padding: 5px 0;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
		font-size: 13px;
	}
	button.row.pick {
		width: 100%;
		padding: 6px 4px;
	}
	.row:hover {
		background: var(--surface-2);
	}
	.row.sel {
		background: var(--accent-soft);
	}
	.name {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.badge {
		font-size: 11px;
		font-weight: 600;
		color: var(--gold);
		box-shadow: inset 0 0 0 1px var(--gold);
		border-radius: 8px;
		padding: 0 6px;
	}
	.badge.tasted {
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	.tasted {
		color: var(--accent);
		font-weight: 600;
	}
	.hint,
	.missing {
		font-size: 12px;
	}
	.hint {
		margin: 4px 0;
	}
	.missing p {
		max-height: 120px;
		overflow-y: auto;
	}
	@media (max-width: 860px) {
		.layout {
			grid-template-columns: 1fr;
			height: auto;
		}
		.map {
			height: 60vh;
		}
		aside {
			max-height: 60vh;
		}
		.seg.small {
			margin-left: 0;
		}
	}
	.region-page {
		margin-left: 10px;
		font-size: 13px;
		font-weight: 500;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.region-page:hover {
		color: var(--accent);
	}
</style>
