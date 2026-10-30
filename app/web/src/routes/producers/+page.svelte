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
	const HAVE = [
		{ id: '', label: 'All' },
		{ id: 'tasted', label: 'Tasted' },
		{ id: 'cellar', label: 'In cellar' }
	];

	const params = $derived(page.url.searchParams);
	const q = $derived(params.get('q') ?? '');
	const have = $derived(params.get('have') ?? '');
	const selection = $derived(readSelection(params, FACETS));

	const base = $derived(
		all.filter(
			(p) =>
				textMatch(q, p.name, p.winemaker, p.village, p.notes) &&
				(have !== 'tasted' || p.tastings > 0) &&
				(have !== 'cellar' || p.bottles > 0)
		)
	);
	const shown = $derived(applyFacets(base, FACETS, selection));
	const facets = $derived(FACETS.map((facet) => ({ facet, options: facetOptions(base, FACETS, selection, facet) })));

	function addFilter(key: string, value: string) {
		if (!selection[key].includes(value)) setParams({ [key]: [...selection[key], value] });
	}

	const clearAll = () => setParams({ q: null, have: null, ...Object.fromEntries(FACETS.map((f) => [f.key, null])) });
</script>

<svelte:head><title>Producers · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Producers</h1>
	<a class="btn icon primary" href={links.newProducer()} title="Add a producer" aria-label="Add a producer"><span class="plus">+</span><Icon name="person" size={15} /></a>
</div>

<DirectoryFilters
	{q}
	placeholder="Search name, winemaker, village, notes…"
	{facets}
	{selection}
	extraActive={Boolean(have)}
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
		</span>
	</div>
	{#if shown.length}
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
</style>
