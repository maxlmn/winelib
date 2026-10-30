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
	import {
		LIST_KEYS, PERIODS, activeCount, emptyFilters, grapeOptions, filterTastings, filterVisits, fromParams, isoDay, occasions, options,
		stats, toMarkdown, toParams, wineName
	} from '#lib/components/tastings/journal.ts';
	import type { ListKey, Period, TastingFilters } from '#lib/components/tastings/journal.ts';
	import { FALLBACK_REGION, TYPE_COLORS } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	let { data } = $props();

	const VIEWS = [
		{ id: 'cards', label: 'Cards' },
		{ id: 'list', label: 'List' },
		{ id: 'map', label: 'Map' },
		{ id: 'trends', label: 'Trends' }
	];
	const LABELS: Record<ListKey, string> = {
		color: 'Color', region: 'Region', producer: 'Producer', appellation: 'Appellation', grape: 'Grape', vintage: 'Vintage', loc: 'Location'
	};

	const journal = $derived(data.journal);
	const params = $derived(page.url.searchParams);
	const filters = $derived(fromParams(params));
	const view = $derived(VIEWS.find((v) => v.id === params.get('view'))?.id ?? 'cards');
	const selectedPlace = $derived(Number(params.get('place')) || null);

	const tastings = $derived(filterTastings(journal.tastings, filters));
	const visits = $derived(filterVisits(journal, filters));
	const cards = $derived(occasions(journal, tastings, visits));
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

	const kpis = $derived([
		{ label: 'Wines tasted', value: s.wines, all: sAll.wines },
		{ label: 'Producers', value: s.producers, all: sAll.producers },
		{ label: 'Unique wines', value: s.unique, all: sAll.unique },
		{ label: 'Michelin stars', value: s.stars, all: sAll.stars, gold: true }
	]);
</script>

<svelte:head><title>Tasting Notes · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Tasting Notes</h1>
	<div class="actions">
		<a class="btn icon primary" href={links.newTasting()} title="Add a tasting" aria-label="Add a tasting"><span class="plus">+</span><Icon name="glass" size={15} /></a>
		<a class="btn icon" href={links.newVisit()} title="Add a restaurant visit" aria-label="Add a restaurant visit"><span class="plus">+</span><Icon name="pin" size={15} /></a>
		<button class="btn" onclick={exportMarkdown} disabled={!tastings.length}>↓ Export</button>
	</div>
</div>

<div class="kpis">
	{#each kpis as k}
		<div class="kpi card">
			<div class="label">{k.label}</div>
			<div class="value num" class:gold={k.gold && k.value}>{k.value}{k.gold && k.value ? ' ★' : ''}</div>
			<div class="sub muted num">{k.value !== k.all ? `of ${k.all}` : 'all notes'}</div>
		</div>
	{/each}
</div>

<TastingRibbon {tastings} />

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

<div class="panel card">
	<div class="tabs">
		{#each VIEWS as v}
			<button class:on={view === v.id} onclick={() => setParams({ view: v.id === 'cards' ? null : v.id })}>{v.label}</button>
		{/each}
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
			<JournalCards occasions={cards} regionColors={data.regionColors} />
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
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.btn.primary:hover {
		color: white;
		filter: brightness(1.05);
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.kpis {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 12px;
		margin-bottom: 14px;
	}
	.kpi {
		padding: 14px 16px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.value {
		font-size: 22px;
		font-weight: 650;
		letter-spacing: -0.01em;
		margin: 2px 0;
	}
	.value.gold {
		color: var(--gold);
	}
	.sub {
		font-size: 12px;
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
