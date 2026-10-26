<script lang="ts">
	import RegionName from '#lib/components/RegionName.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import CellarCards from '#lib/components/CellarCards.svelte';
	import CellarTable from '#lib/components/CellarTable.svelte';
	import MultiSelect from '#lib/components/MultiSelect.svelte';
	import ShelfMap from '#lib/components/ShelfMap.svelte';
	import VintageHeatmap from '#lib/components/VintageHeatmap.svelte';
	import PriceChanges from '#lib/components/cellar/PriceChanges.svelte';
	import BordeauxIndex from '#lib/components/cellar/BordeauxIndex.svelte';
	import StorageDonuts from '#lib/components/cellar/StorageDonuts.svelte';
	import { FALLBACK_REGION, TYPE_COLORS } from '#lib/colors.ts';
	import { activeCount, emptyFilters, filterLocations, filterWines, fromParams, grapeOptions, options, toParams, totals } from '#lib/filters.ts';
	import type { Filters, ListKey } from '#lib/filters.ts';
	import Change from '#lib/components/Change.svelte';
	import { inCurrency, pct } from '#lib/format.ts';
	import { appSettings, configured } from '#lib/settings.svelte.ts';
	import { links } from '#lib/links.ts';

	let { data } = $props();

	const VIEWS = [
		{ id: 'cards', label: 'Cards' },
		{ id: 'shelves', label: 'Shelf map' },
		{ id: 'list', label: 'List' },
		{ id: 'vintages', label: 'Vintages' },
		{ id: 'prices', label: 'Price changes' },
		{ id: 'bi', label: 'Bordeaux Index', when: 'bordeaux_index' }
	].filter((v) => !v.when || configured(v.when)); // an integration's tab: only when it's set up

	const all = $derived(data.cellar.bottles);
	const filters = $derived(fromParams(page.url.searchParams));
	const view = $derived(page.url.searchParams.get('view') ?? 'cards');
	// Totals in another currency (?cur=GBP), with the Settings page's rates
	const currencies = $derived(Object.keys(appSettings.exchange_rates));
	const cur = $derived(currencies.includes(page.url.searchParams.get('cur') ?? '') ? page.url.searchParams.get('cur')! : appSettings.currency);
	const money = (n: number) => inCurrency(n, cur, appSettings.exchange_rates);

	function setCurrency(c: string) {
		const p = new URLSearchParams(page.url.searchParams.toString());
		if (c === appSettings.currency) p.delete('cur');
		else p.set('cur', c);
		navigate(p);
	}

	const wines = $derived(filterWines(all, filters)); // everything but location
	const shown = $derived(filterLocations(wines, filters));
	const t = $derived(totals(shown));
	const tAll = $derived(totals(all));
	const tLocal = $derived(totals(shown.filter((b) => b.local)));

	function navigate(params: URLSearchParams) {
		// replace: filtering shouldn't flood the back button
		goto(`?${params}`, { replace: true, reset: false });
	}

	const setFilters = (f: Filters) => navigate(toParams(f, page.url.searchParams));
	const setList = (key: ListKey, values: string[]) => setFilters({ ...filters, [key]: values });

	/** On a phone the tab row scrolls sideways: keep the current tab visible. */
	function intoView(el: HTMLElement, on: boolean) {
		// Scrolls the tab row only (scrollIntoView would also scroll the page down to it)
		const show = (yes: boolean) => {
			const row = el.parentElement;
			if (!yes || !row || row.scrollWidth <= row.clientWidth) return;
			const left = el.offsetLeft - row.offsetLeft;
			if (left < row.scrollLeft || left + el.offsetWidth > row.scrollLeft + row.clientWidth)
				row.scrollLeft = left - (row.clientWidth - el.offsetWidth) / 2;
		};
		show(on);
		return { update: show };
	}

	function setView(id: string) {
		const p = new URLSearchParams(page.url.searchParams.toString());
		p.set('view', id);
		navigate(p);
	}

	function toggleLocation(loc: string) {
		setFilters({ ...filters, group: [], loc: filters.loc.length === 1 && filters.loc[0] === loc ? [] : [loc] });
	}

	const regionSwatch = (r: string) => data.regionColors[r] ?? FALLBACK_REGION;
	const typeSwatch = (c: string) => TYPE_COLORS[c];

	function exportMarkdown() {
		const cols: [string, (b: (typeof shown)[number]) => string | number][] = [
			['Qty', (b) => b.qty], ['Color', (b) => b.color ?? ''], ['Region', (b) => regionLabel(b.region)],
			['Producer', (b) => b.producer], ['Cuvée', (b) => b.cuvee], ['Appellation', (b) => b.appellation ?? ''],
			['Grapes', (b) => b.grapes.join(', ')], ['Vintage', (b) => b.vintage], ['Format', (b) => b.format ?? ''],
			['Location', (b) => b.location], ['Purchased', (b) => b.purchase_date ?? ''],
			[`Paid (${cur})`, (b) => Math.round(conv(b.price_base))], [`Market (${cur})`, (b) => Math.round(conv(b.market_base))], ['Scores', (b) => b.scores ?? '']
		];
		function conv(n: number) {
			return cur === appSettings.currency ? n : n / (appSettings.exchange_rates[cur] ?? 1);
		}
		const cell = (v: string | number) => String(v).replace(/\|/g, '\\|');
		const today = new Date().toISOString().slice(0, 10);
		const md = [
			`# Cellar export — ${today}`, '',
			`${t.qty} bottles · cost ${money(t.cost)} · market ${money(t.market)} (${cur})`, '',
			`| ${cols.map(([h]) => h).join(' | ')} |`, `|${'---|'.repeat(cols.length)}`,
			...shown.map((b) => `| ${cols.map(([, f]) => cell(f(b))).join(' | ')} |`)
		].join('\n');
		const a = Object.assign(document.createElement('a'), {
			href: URL.createObjectURL(new Blob([md], { type: 'text/markdown' })),
			download: `cellar_${today.replace(/-/g, '')}.md`
		});
		a.click();
		URL.revokeObjectURL(a.href);
	}
	// Local totals only once some locations are set as not local (Settings): until then they're the same as the others
	const hasLocal = $derived(appSettings.non_local_keywords.length > 0);
</script>

<svelte:head><title>Cellar · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Cellar</h1>
	<div class="head-actions">
		<div class="currency" role="group" aria-label="Currency of the totals">
			{#each currencies as c (c)}
				<button class:on={c === cur} onclick={() => setCurrency(c)}>{c}</button>
			{/each}
		</div>
		<a class="btn" href="{links.wineList()}?{toParams(filters)}">Wine list</a>
		<button class="btn" onclick={exportMarkdown}>↓ Export</button>
	</div>
</div>

<div class="kpis">
	<div class="kpi card">
		<div class="label">Bottles</div>
		<div class="value num">{t.qty}</div>
		{#if t.qty !== tAll.qty}<div class="sub muted">of {tAll.qty}</div>{/if}
	</div>
	<div class="kpi card">
		<div class="label">Cost</div>
		<div class="value num">{t.cost ? money(t.cost) : '–'}</div>
		{#if hasLocal && tLocal.cost}<div class="sub muted">{appSettings.local_label} {money(tLocal.cost)}</div>{/if}
	</div>
	{#each [{ label: 'Market value', s: t }, ...(hasLocal ? [{ label: `${appSettings.local_label} market value`, s: tLocal }] : [])] as k}
		{@const p = pct(k.s.cost, k.s.market)}
		<div class="kpi card">
			<div class="label">{k.label}</div>
			<div class="value num">{k.s.market ? money(k.s.market) : '–'}</div>
			{#if k.s.market}<div class="sub num"><Change value={p} digits={1} /></div>{/if}
		</div>
	{/each}
</div>

{#if shown.length}
	<div class="storage card"><StorageDonuts bottles={shown} {money} /></div>
{/if}

<div class="filters card">
	<input
		class="search"
		type="search"
		placeholder="Search producer, cuvée, appellation, grape…"
		value={filters.q}
		oninput={(e) => setFilters({ ...filters, q: e.currentTarget.value })}
	/>
	<div class="row">
		<MultiSelect label="Color" options={options(all, 'color')} selected={filters.color} onchange={(v) => setList('color', v)} swatch={typeSwatch} />
		<MultiSelect label="Region" options={options(all, 'region')} selected={filters.region} onchange={(v) => setList('region', v)} swatch={regionSwatch} format={regionLabel} />
		<MultiSelect label="Producer" options={options(all, 'producer')} selected={filters.producer} onchange={(v) => setList('producer', v)} />
		<MultiSelect label="Appellation" options={options(all, 'appellation')} selected={filters.appellation} onchange={(v) => setList('appellation', v)} />
		<MultiSelect label="Grape" options={grapeOptions(all)} selected={filters.grape} onchange={(v) => setList('grape', v)} />
		<MultiSelect label="Vintage" options={options(all, 'vintage')} selected={filters.vintage} onchange={(v) => setList('vintage', v)} />
		<MultiSelect label="Storage" options={options(all, 'location_group')} selected={filters.group} onchange={(v) => setList('group', v)} />
		<MultiSelect label="Bin" options={options(all, 'location')} selected={filters.loc} onchange={(v) => setList('loc', v)} />
		{#if activeCount(filters)}
			<button class="reset" onclick={() => setFilters(emptyFilters())}>Clear all</button>
		{/if}
	</div>
	{#if activeCount(filters)}
		<div class="chips">
			{#each Object.entries(filters) as [key, values]}
				{#if Array.isArray(values)}
					{#each values as v}
						<button class="chip" onclick={() => setList(key as ListKey, values.filter((x) => x !== v))}>{#if key === 'region'}<RegionName name={v} />{:else}{v}{/if} ✕</button>
					{/each}
				{/if}
			{/each}
		</div>
	{/if}
</div>

<div class="panel card">
	<div class="tabs">
		{#each VIEWS as v}
			<button class:on={view === v.id} onclick={() => setView(v.id)} use:intoView={view === v.id}>{v.label}</button>
		{/each}
		<span class="count muted num">{shown.length} lines · {t.qty} bottles</span>
	</div>
	<div class="body">
		{#if view === 'shelves'}
			<ShelfMap
				locations={data.cellar.locations}
				{all}
				matching={wines}
				selected={filters.loc}
				regionColors={data.regionColors}
				onselect={toggleLocation}
			/>
			{#if filters.loc.length}
				<h3 class="sub-h">In {filters.loc.join(', ')}</h3>
				<CellarTable bottles={shown} regionColors={data.regionColors} />
			{/if}
		{:else if view === 'bi'}
			<BordeauxIndex />
		{:else if shown.length === 0}
			<p class="muted">No bottles match these filters.</p>
		{:else if view === 'cards'}
			<CellarCards bottles={shown} regionColors={data.regionColors} />
		{:else if view === 'list'}
			<CellarTable bottles={shown} regionColors={data.regionColors} />
		{:else if view === 'prices'}
			<PriceChanges bottles={shown} />
		{:else if view === 'vintages'}
			<VintageHeatmap
				bottles={shown}
				regionColors={data.regionColors}
				onpick={(region, vintages) => setFilters({ ...filters, region: [region], vintage: vintages })}
			/>
		{/if}
	</div>
</div>

<style>
	.head-actions {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
		justify-content: flex-end;
	}
	.currency {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}
	.currency button {
		border: none;
		background: none;
		padding: 5px 9px;
		font-size: 12px;
		cursor: pointer;
		color: var(--muted);
	}
	.currency button.on {
		background: var(--accent);
		color: #fff;
	}
	.kpis {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 12px;
		margin-bottom: 14px;
	}
	.kpi {
		padding: 14px 16px;
	}
	.storage {
		padding: 14px 16px;
		margin-bottom: 14px;
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
	.panel {
		overflow: visible;
	}
	.tabs {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 8px 10px 0;
		border-bottom: 1px solid var(--border);
		/* Too many tabs for a phone: the row scrolls sideways instead of overflowing the page */
		overflow-x: auto;
		scrollbar-width: none;
	}
	.tabs::-webkit-scrollbar {
		display: none;
	}
	.tabs button {
		flex: none;
		white-space: nowrap;
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
		padding-left: 12px;
		font-size: 12px;
		white-space: nowrap;
	}
	@media (max-width: 760px) {
		.tabs {
			padding: 6px 6px 0;
			gap: 0;
			/* a fade at the edges says there's more to scroll to */
			mask-image: linear-gradient(to right, transparent 0, #000 12px, #000 calc(100% - 24px), transparent 100%);
		}
		.tabs button {
			padding: 8px 10px;
		}
		.count {
			display: none; /* the totals above already say it */
		}
	}
	.body {
		padding: 16px;
	}
	.sub-h {
		margin: 24px 0 8px;
		font-size: 14px;
	}
</style>
