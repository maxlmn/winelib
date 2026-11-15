<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { setParams } from '#lib/url.ts';
	import { page } from '$app/state';
	import type { ProducerRow } from '#lib/api/directory.ts';
	import DirectoryFilters from '#lib/components/directory/DirectoryFilters.svelte';
	import ProducerTable from '#lib/components/directory/ProducerTable.svelte';
	import { applyFacets, facetOptions, readSelection, textMatch } from '#lib/components/directory/facets.ts';
	import type { Facet } from '#lib/components/directory/facets.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { plural } from '#lib/format.ts';

	let { data } = $props();

	const all = $derived(data.producers);
	const regionColors = $derived(new Map(all.map((p) => [p.region, p.color])));

	const FACETS: Facet<ProducerRow>[] = [
		{ key: 'region', label: 'Region', values: (p) => [p.region], swatch: (v) => regionColors.get(v) ?? FALLBACK_REGION },
		{ key: 'subregion', label: 'Sub-region', values: (p) => [p.subregion] },
		{ key: 'village', label: 'Village', values: (p) => [p.village] },
		{ key: 'winemaker', label: 'Winemaker', values: (p) => [p.winemaker] },
		{ key: 'list', label: 'Lists', values: (p) => p.lists }
	];
	// Yours (a wine of theirs in WineLib, tasted, in the cellar, on a list) first: the directory also holds the
	// producers it ships with, thousands you may never have heard of
	const HAVE = [
		{ id: 'yours', label: 'Yours' },
		{ id: 'tasted', label: 'Tasted' },
		{ id: 'cellar', label: 'In cellar' },
		{ id: 'all', label: 'All' }
	];
	const yours = (p: ProducerRow) => p.wines > 0 || p.tastings > 0 || p.bottles > 0 || p.lists.length > 0;
	const anyYours = $derived(all.some(yours));

	const params = $derived(page.url.searchParams);
	const q = $derived(params.get('q') ?? '');
	// none asked: yours, when you have any
	const have = $derived(params.get('have') ?? (anyYours ? 'yours' : 'all'));
	const selection = $derived(readSelection(params, FACETS));

	const base = $derived(
		all.filter(
			(p) =>
				textMatch(q, p.name, p.winemaker, p.village, p.notes) &&
				(have !== 'yours' || yours(p)) &&
				(have !== 'tasted' || p.tastings > 0) &&
				(have !== 'cellar' || p.bottles > 0)
		)
	);
	const shown = $derived(applyFacets(base, FACETS, selection));
	const facets = $derived(FACETS.map((facet) => ({ facet, options: facetOptions(base, FACETS, selection, facet) })));

	function addFilter(key: string, value: string) {
		if (!selection[key].includes(value)) setParams({ [key]: [...selection[key], value] });
	}

	// Two modes: the producers over the map (the default), or the table, the page's whole width (view=table)
	const onMap = $derived(params.get('view') !== 'table');
	// the map behind: the regions of the producers shown, deeper where there are more of them; a producer chosen in the
	// column flies it to where its wines come from
	const counts = $derived.by(() => {
		const out: Record<string, number> = {};
		for (const p of shown) if (p.region) out[p.region] = (out[p.region] ?? 0) + 1;
		return out;
	});
	let pointed = $state<ProducerRow | null>(null);
	let pointTimer: ReturnType<typeof setTimeout> | undefined;
	function point(p: ProducerRow, wait = 0) {
		clearTimeout(pointTimer);
		if (wait) pointTimer = setTimeout(() => (pointed = p), wait);
		else pointed = p;
	}
	// the column's list in steps (the whole directory runs to thousands)
	const STEP = 100;
	let limit = $state(STEP);
	$effect(() => {
		void shown;
		limit = STEP;
	});

	const clearAll = () => setParams({ q: null, have: null, ...Object.fromEntries(FACETS.map((f) => [f.key, null])) });
</script>

<svelte:head><title>Producers · WineLib</title></svelte:head>

{#if onMap}
	<HomeMap full {counts} focus={pointed ? { producerId: pointed.id, region: pointed.region } : null} />
{/if}

<div class="page-head">
	<h1>Producers</h1>
	<div class="actions">
		<div class="mode" role="group" aria-label="How the producers are shown">
			<button class:on={onMap} aria-pressed={onMap} onclick={() => setParams({ view: null })} title="The producers as a list, over the map">On the map</button>
			<button class:on={!onMap} aria-pressed={!onMap} onclick={() => setParams({ view: 'table' })} title="The table, the page's whole width">Tables</button>
		</div>
		<a class="btn icon primary" href={links.newProducer()} title="Add a producer" aria-label="Add a producer"><span class="plus">+</span><Icon name="person" size={15} /></a>
	</div>
</div>

<DirectoryFilters
	{q}
	placeholder="Search name, winemaker, village, notes…"
	{facets}
	{selection}
	extraActive={params.has('have')}
	onsearch={(v) => setParams({ q: v })}
	onselect={(key, values) => setParams({ [key]: values })}
	onclear={clearAll}
>
	{#snippet extra()}
		<div class="seg">
			{#each HAVE as h}
				<button class:on={have === h.id} onclick={() => setParams({ have: h.id })}>{h.label}</button>
			{/each}
		</div>
	{/snippet}
</DirectoryFilters>

<div class="panel card">
	<div class="bar">
		<span class="count muted num">
			{shown.length === all.length ? `${all.length} producers` : `${shown.length} of ${all.length} producers`}
			{#if have === 'yours' && !q}· <button class="link" onclick={() => setParams({ have: 'all' })}>the whole directory</button>{/if}
		</span>
	</div>
	{#if shown.length && onMap}
		<!-- a producer a line: clicked (or hovered, Settings › Map) the map flies to where its wines come from -->
		<ul class="producers">
			{#each shown.slice(0, limit) as p (p.id)}
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
				<li
					class:shown={pointed?.id === p.id}
					onpointerenter={(e) => e.pointerType === 'mouse' && appSettings.map_follow === 'hover' && point(p, 180)}
					onclick={(e) => !(e.target as HTMLElement).closest('a, button') && point(p)}
				>
					<span class="dot" style:background={p.color ?? FALLBACK_REGION}></span>
					<div class="p-main">
						<a href={links.producer(p.id)}>{p.name}</a>
						<div class="muted p-sub">{[p.region ? regionLabel(p.region) : null, p.village].filter(Boolean).join(' · ')}</div>
					</div>
					<div class="muted num p-counts">
						{[p.tastings ? plural(p.tastings, 'tasting') : '', p.bottles ? plural(p.bottles, 'bottle') : ''].filter(Boolean).join(' · ')}
					</div>
				</li>
			{/each}
		</ul>
		{#if shown.length > limit}
			<button class="more-btn" onclick={() => (limit += STEP)}>Show {Math.min(STEP, shown.length - limit)} more ({shown.length - limit} left)</button>
		{/if}
	{:else if shown.length}
		<ProducerTable rows={shown} onfilter={(key, value) => addFilter(key, value)} />
	{:else}
		<p class="muted empty">No producers match these filters.</p>
	{/if}
</div>

<style>
	.bar {
		padding: 10px 14px;
		border-bottom: 1px solid var(--border);
		font-size: 12px;
	}
	.empty {
		padding: 16px;
		margin: 0;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
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
	/* the producers in the column: a line each, the one on the map tinted */
	.producers {
		list-style: none;
		margin: 0;
		padding: 6px 8px 10px;
	}
	.producers li {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 7px 8px;
		border-radius: 6px;
		font-size: 13px;
		cursor: pointer;
		transition: background 0.15s;
	}
	.producers li + li {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.producers li:hover {
		background: color-mix(in srgb, var(--accent) 5%, transparent);
	}
	.producers li.shown {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}
	.dot {
		flex: none;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		align-self: center;
	}
	.p-main {
		flex: 1;
		min-width: 0;
	}
	.p-main a {
		font-weight: 600;
	}
	.p-sub,
	.p-counts {
		font-size: 12px;
	}
	.p-counts {
		flex: none;
		text-align: right;
	}
	.more-btn {
		display: block;
		margin: 0 auto 12px;
		padding: 6px 14px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		font: inherit;
		font-size: 12px;
		color: var(--text);
		cursor: pointer;
	}
	.link {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		color: var(--link);
		cursor: pointer;
	}
	.link:hover {
		color: var(--accent);
	}
</style>
