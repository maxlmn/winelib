<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { setParams } from '#lib/url.ts';
	import RegionName from '#lib/components/RegionName.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { page } from '$app/state';
	import MultiSelect from '#lib/components/MultiSelect.svelte';
	import JournalCards from '#lib/components/tastings/JournalCards.svelte';
	import TastingMap from '#lib/components/tastings/TastingMap.svelte';
	import TastingTable from '#lib/components/tastings/TastingTable.svelte';
	import TastingTrends from '#lib/components/tastings/TastingTrends.svelte';
	import TastingRibbon from '#lib/components/tastings/TastingRibbon.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import type { Tasting } from '#lib/api/tastings.ts';
	import {
		LIST_KEYS, PERIODS, activeCount, emptyFilters, grapeOptions, filterTastings, filterVisits, fromParams, isoDay, occasions, options,
		stats, toMarkdown, toParams, wineName
	} from '#lib/components/tastings/journal.ts';
	import type { ListKey, Period, TastingFilters } from '#lib/components/tastings/journal.ts';
	import { FALLBACK_REGION, TYPE_COLORS } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	let { data } = $props();

	// Two modes: the notes as cards over the map (the default), or the tables, wide (the views below; "map" is the
	// places' map, the restaurants and homes)
	const VIEWS = [
		{ id: 'list', label: 'List' },
		{ id: 'map', label: 'Places' },
		{ id: 'trends', label: 'Trends' }
	];
	const LABELS: Record<ListKey, string> = {
		color: 'Color', region: 'Region', producer: 'Producer', appellation: 'Appellation', grape: 'Grape', vintage: 'Vintage', loc: 'Location'
	};

	const journal = $derived(data.journal);
	const params = $derived(page.url.searchParams);
	const filters = $derived(fromParams(params));
	const view = $derived(VIEWS.find((v) => v.id === params.get('view'))?.id ?? 'cards');
	const onMap = $derived(view === 'cards');
	// a wine pointed at (in the cards, or along the ribbon): the map flies to it
	// ...or a place (an occasion's header): the map pins it
	let pointed = $state<Tasting | null>(null);
	let pinned = $state<[number, number] | null>(null);
	let pointTimer: ReturnType<typeof setTimeout> | undefined;
	function point(t: Tasting, wait = 180) {
		clearTimeout(pointTimer);
		const go = () => ((pointed = t), (pinned = null));
		if (wait) pointTimer = setTimeout(go, wait);
		else go();
	}
	function pointPlace(where: [number, number]) {
		clearTimeout(pointTimer);
		pointTimer = setTimeout(() => (pinned = where), 180);
	}
	// the tables: back on the one last opened (this visit), the list at first
	let lastTable = $state('list');
	$effect(() => {
		if (!onMap) lastTable = view;
	});
	const selectedPlace = $derived(Number(params.get('place')) || null);

	const tastings = $derived(filterTastings(journal.tastings, filters));
	const visits = $derived(filterVisits(journal, filters));
	const cards = $derived(occasions(journal, tastings, visits));
	// with nothing pointed at, the latest tasting shown: the latest evening's last wine
	const latest = $derived(cards.find((o) => o.wines.length)?.wines.at(-1) ?? null);
	const shownWine = $derived(pointed ?? latest);
	const focus = $derived(pinned ? { point: pinned } : shownWine ? { wineId: shownWine.wine_id, region: shownWine.region } : null);
	const s = $derived(stats(journal, tastings, visits));
	const sAll = $derived(stats(journal, journal.tastings, journal.visits));

	const locationOptions = $derived(
		options(journal.tastings, 'location', journal.visits.map((v) => journal.places[v.place_id]?.name).filter((n) => n !== undefined))
	);
	const wineLabel = $derived.by(() => {
		const t = filters.wine ? journal.tastings.find((x) => x.wine_id === filters.wine) : undefined;
		return t ? wineName(t) : `Wine #${filters.wine}`;
	});

	const setFilters = (f: TastingFilters, changes: Record<string, string | null> = {}) => setParams(changes, toParams(f, params));
	const setList = (key: ListKey, values: string[]) => setFilters({ ...filters, [key]: values });

	function setPeriod(period: Period) {
		// A custom range starts from whatever the previous period showed
		const today = isoDay(new Date());
		const from = filters.period === '30d' ? isoDay(new Date(Date.now() - 30 * 864e5)) : `${today.slice(0, 4)}-01-01`;
		setFilters({ ...filters, period, from: period === 'custom' ? filters.from || from : '', to: period === 'custom' ? filters.to || today : '' });
	}

	const regionSwatch = (r: string) => data.regionColors[r] ?? FALLBACK_REGION;
	const typeSwatch = (c: string) => TYPE_COLORS[c];

	function exportMarkdown() {
		const a = Object.assign(document.createElement('a'), {
			href: URL.createObjectURL(new Blob([toMarkdown(journal, tastings)], { type: 'text/markdown' })),
			download: `tastings_${isoDay(new Date()).replace(/-/g, '')}.md`
		});
		a.click();
		URL.revokeObjectURL(a.href);
	}

	// the figures of what's shown (the filters'), as one line; "of" the whole journal's when filtered
	const figures = $derived([
		{ label: 'wines tasted', value: s.wines, all: sAll.wines },
		{ label: 'producers', value: s.producers, all: sAll.producers },
		{ label: 'unique wines', value: s.unique, all: sAll.unique },
		{ label: 'Michelin stars', value: s.stars, all: sAll.stars, gold: true }
	]);
</script>

<svelte:head><title>Tasting Notes · WineLib</title></svelte:head>

<div class="page-head">
	<div>
		<h1>Tasting Notes</h1>
		<p class="stats">
			{#each figures as k (k.label)}
				<span><b class="num" class:gold={k.gold && k.value}>{k.value}{k.gold && k.value ? ' ★' : ''}</b> {k.label}{#if k.value !== k.all}<span class="muted">&nbsp;of {k.all}</span>{/if}</span>
			{/each}
		</p>
	</div>
	<div class="actions">
		<div class="mode" role="group" aria-label="How the notes are shown">
			<button class:on={onMap} aria-pressed={onMap} onclick={() => setParams({ view: null })} title="The notes as cards, over the map">On the map</button>
			<button class:on={!onMap} aria-pressed={!onMap} onclick={() => setParams({ view: lastTable })} title="The list, the places and the trends, the page's whole width">Tables</button>
		</div>
		<a class="btn icon primary" href={links.newTasting()} title="Add a tasting" aria-label="Add a tasting"><span class="plus">+</span><Icon name="glass" size={15} /></a>
		<a class="btn icon" href={links.newVisit()} title="Add a restaurant visit" aria-label="Add a restaurant visit"><span class="plus">+</span><Icon name="pin" size={15} /></a>
		<!-- the latest evening (its last wine, as the map shows it), to write its notes -->
		{#if latest}
			<a
				class="btn icon"
				href={links.tasting(latest.id)}
				title="The last evening's notes: {[latest.producer, latest.cuvee, latest.vintage].filter(Boolean).join(' ')}"
				aria-label="Write the last evening's notes"><Icon name="edit" size={15} /></a
			>
		{/if}
		<button class="btn" onclick={exportMarkdown} disabled={!tastings.length}>↓ Export</button>
	</div>
</div>

{#if onMap}
	<HomeMap full by="tasted" {focus} />
	<TastingRibbon
		{tastings}
		label="Every wine, oldest on the left: its region’s colour, its own below. Sweep it, or replay it, the map following"
		onwine={(t, now) => point(t, now ? 0 : 90)}
		shown={shownWine?.id ?? null}
	/>
{:else}
	<TastingRibbon {tastings} />
{/if}

<div class="filters card">
	<input
		class="search"
		type="search"
		placeholder="Search producer, cuvée, appellation, grape, notes…"
		value={filters.q}
		oninput={(e) => setFilters({ ...filters, q: e.currentTarget.value })}
	/>
	<div class="row">
		<MultiSelect label="Color" options={options(journal.tastings, 'color')} selected={filters.color} onchange={(v) => setList('color', v)} swatch={typeSwatch} />
		<MultiSelect label="Region" options={options(journal.tastings, 'region')} selected={filters.region} onchange={(v) => setList('region', v)} swatch={regionSwatch} format={regionLabel} />
		<MultiSelect label="Producer" options={options(journal.tastings, 'producer')} selected={filters.producer} onchange={(v) => setList('producer', v)} />
		<MultiSelect label="Appellation" options={options(journal.tastings, 'appellation')} selected={filters.appellation} onchange={(v) => setList('appellation', v)} />
		<MultiSelect label="Grape" options={grapeOptions(journal.tastings)} selected={filters.grape} onchange={(v) => setList('grape', v)} />
		<MultiSelect label="Vintage" options={options(journal.tastings, 'vintage')} selected={filters.vintage} onchange={(v) => setList('vintage', v)} />
		<MultiSelect label="Location" options={locationOptions} selected={filters.loc} onchange={(v) => setList('loc', v)} />
		<div class="period">
			<select aria-label="Period" value={filters.period} onchange={(e) => setPeriod(e.currentTarget.value as Period)}>
				{#each PERIODS as p}<option value={p.id}>{p.label}</option>{/each}
			</select>
			{#if filters.period === 'custom'}
				<input type="date" aria-label="From" value={filters.from} max={filters.to || undefined} onchange={(e) => setFilters({ ...filters, from: e.currentTarget.value })} />
				<span class="muted">–</span>
				<input type="date" aria-label="To" value={filters.to} min={filters.from || undefined} onchange={(e) => setFilters({ ...filters, to: e.currentTarget.value })} />
			{/if}
		</div>
		{#if activeCount(filters)}
			<button class="reset" onclick={() => setFilters(emptyFilters(filters.period), { place: null })}>Clear all</button>
		{/if}
	</div>
	{#if activeCount(filters)}
		<div class="chips">
			{#if filters.wine}<button class="chip" onclick={() => setFilters({ ...filters, wine: null })}>{wineLabel} ✕</button>{/if}
			{#if filters.q}<button class="chip" onclick={() => setFilters({ ...filters, q: '' })}>“{filters.q}” ✕</button>{/if}
			{#each LIST_KEYS as key}
				{#each filters[key] as v}
					<button class="chip" title={LABELS[key]} onclick={() => setList(key, filters[key].filter((x) => x !== v))}>{#if key === 'region'}<RegionName name={v} />{:else}{v}{/if} ✕</button>
				{/each}
			{/each}
		</div>
	{/if}
</div>

<!-- The cards sit on the page itself: not cards in a card -->
<div class="panel card">
	<div class="tabs" class:bare={onMap}>
		{#if onMap}
			<h2>Notes</h2>
		{:else}
			{#each VIEWS as v}
				<button class:on={view === v.id} onclick={() => setParams({ view: v.id })}>{v.label}</button>
			{/each}
		{/if}
		<span class="count muted num">
			{plural(tastings.length, 'wine')} · {plural(cards.length, 'occasion')}
		</span>
	</div>
	<div class="body">
		{#if !cards.length}
			<div class="empty">
				<p class="muted">No notes match these filters{filters.period !== 'all' ? ` in this period` : ''}.</p>
				{#if filters.period !== 'all'}<button class="btn" onclick={() => setPeriod('all')}>Show all time</button>{/if}
			</div>
		{:else if view === 'cards'}
			<JournalCards occasions={cards} regionColors={data.regionColors} onwine={(w) => point(w)} shown={pinned ? null : (shownWine?.id ?? null)} onplace={pointPlace} />
		{:else if view === 'list'}
			{#if tastings.length}
				<TastingTable {tastings} places={journal.places} regionColors={data.regionColors} />
			{:else}
				<p class="muted">Only restaurant visits here: no wines to list.</p>
			{/if}
		{:else if view === 'map'}
			<TastingMap
				{tastings}
				{visits}
				places={journal.places}
				selected={selectedPlace}
				onselect={(id) => setParams({ place: id ? String(id) : null })}
				onfilter={(name) => setFilters({ ...filters, loc: [name] }, { view: null, place: null })}
			/>
		{:else if view === 'trends'}
			<TastingTrends
				{tastings}
				{visits}
				places={journal.places}
				regionColors={data.regionColors}
				selectedRegions={filters.region}
				onregion={(regions) => setList('region', regions)}
			/>
		{/if}
	</div>
</div>

<style>
	/* on the map: a heading in place of the tables' tabs */
	.tabs.bare {
		align-items: baseline;
		padding: 12px 16px 10px;
	}
	.tabs.bare h2 {
		margin: 0;
		font-size: 15px;
	}
	.mode {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.mode button {
		border: none;
		background: none;
		padding: 6px 11px;
		font: inherit;
		font-size: 13px;
		cursor: pointer;
		color: var(--muted);
	}
	.mode button.on {
		background: var(--accent);
		color: var(--on-accent);
	}
	/* in the column over the map: the title, its buttons on a line of their own under it */
	:global(html.map-full) .page-head {
		flex-direction: column;
		align-items: stretch;
		gap: 10px;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.btn.primary:hover {
		color: var(--on-accent);
		filter: brightness(1.05);
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.page-head h1 {
		margin: 0;
	}
	.stats {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 14px;
		margin: 4px 0 0;
		font-size: 13px;
		color: var(--muted);
	}
	.stats b {
		color: var(--text);
		font-weight: 600;
	}
	.stats b.gold {
		color: var(--gold-text);
	}
	.filters {
		padding: 12px;
		margin-bottom: 14px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		position: relative;
		z-index: 10;
	}
	.search {
		width: 100%;
		padding: 9px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		outline: none;
	}
	.search:focus {
		border-color: var(--accent);
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		align-items: center;
	}
	.period {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}
	.period select,
	.period input {
		padding: 6px 8px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
	}
	.period select {
		border-color: var(--accent);
		cursor: pointer;
	}
	.reset {
		border: none;
		background: none;
		color: var(--accent);
		cursor: pointer;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.chip {
		border: none;
		border-radius: 12px;
		padding: 2px 10px;
		background: var(--accent-soft);
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
	}
	.tabs {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
		padding: 8px 10px 0;
		border-bottom: 1px solid var(--border);
	}
	.tabs button {
		border: none;
		background: none;
		padding: 8px 12px;
		cursor: pointer;
		color: var(--muted);
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
	}
	.tabs button.on {
		color: var(--text);
		border-bottom-color: var(--accent);
		font-weight: 600;
	}
	.count {
		margin-left: auto;
		font-size: 12px;
		padding: 0 8px;
	}
	.body {
		padding: 16px;
	}
	.empty {
		text-align: center;
		padding: 30px 0;
	}
	.empty p {
		margin: 0 0 12px;
	}
	@media (max-width: 760px) {
		.body {
			padding: 12px;
		}
		.count {
			width: 100%;
			order: 10;
			margin: 0;
			padding: 4px 4px 8px;
		}
	}
</style>
