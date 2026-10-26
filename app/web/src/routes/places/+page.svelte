<script lang="ts">
	import { setParams } from '#lib/url.ts';
	import { page } from '$app/state';
	import type { PlaceRow } from '#lib/api/directory.ts';
	import DirectoryFilters from '#lib/components/directory/DirectoryFilters.svelte';
	import PlaceTable from '#lib/components/directory/PlaceTable.svelte';
	import PlacesMap from '#lib/components/directory/PlacesMap.svelte';
	import { applyFacets, facetOptions, readSelection, textMatch } from '#lib/components/directory/facets.ts';
	import type { Facet } from '#lib/components/directory/facets.ts';
	import { links } from '#lib/links.ts';

	let { data } = $props();

	const starLabel = (n: number) => (n ? `${n} star${n === 1 ? '' : 's'}` : 'No star');

	const FACETS: Facet<PlaceRow>[] = [
		{ key: 'country', label: 'Country', values: (p) => [p.country] },
		{ key: 'city', label: 'City', values: (p) => [p.city] },
		{ key: 'type', label: 'Type', values: (p) => [p.type] },
		{ key: 'stars', label: 'Michelin', values: (p) => [starLabel(p.stars)] }
	];
	const VIEWS = [
		{ id: 'list', label: 'List' },
		{ id: 'map', label: 'Map' }
	];

	const all = $derived(data.places);
	const params = $derived(page.url.searchParams);
	const q = $derived(params.get('q') ?? '');
	const visited = $derived(params.get('visited') === '1');
	const view = $derived(params.get('view') ?? 'list');
	const selection = $derived(readSelection(params, FACETS));

	const base = $derived(all.filter((p) => textMatch(q, p.name, p.city, p.notes) && (!visited || p.visits > 0)));
	const shown = $derived(applyFacets(base, FACETS, selection));
	const facets = $derived(FACETS.map((facet) => ({ facet, options: facetOptions(base, FACETS, selection, facet) })));
	const visitedCount = $derived(all.filter((p) => p.visits > 0).length);

	function addFilter(key: string, value: string) {
		if (!selection[key].includes(value)) setParams({ [key]: [...selection[key], value] });
	}

	const clearAll = () => setParams({ q: null, visited: null, ...Object.fromEntries(FACETS.map((f) => [f.key, null])) });
</script>

<svelte:head><title>Places · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Places</h1>
	<div class="actions">
		<a class="btn" href={links.newPlace()}>+ Add place</a>
		<a class="btn primary" href={links.newVisit()}>+ Add visit</a>
	</div>
</div>

<DirectoryFilters
	{q}
	placeholder="Search name, city, notes…"
	{facets}
	{selection}
	extraActive={visited}
	onsearch={(v) => setParams({ q: v })}
	onselect={(key, values) => setParams({ [key]: values })}
	onclear={clearAll}
>
	{#snippet extra()}
		<div class="seg">
			<button class:on={!visited} onclick={() => setParams({ visited: null })}>All</button>
			<button class:on={visited} onclick={() => setParams({ visited: '1' })}>Visited <span class="num">{visitedCount}</span></button>
		</div>
	{/snippet}
</DirectoryFilters>

<div class="panel card">
	<div class="tabs">
		{#each VIEWS as v}
			<button class:on={view === v.id} onclick={() => setParams({ view: v.id === 'list' ? null : v.id })}>{v.label}</button>
		{/each}
		<span class="count muted num">
			{shown.length === all.length ? `${all.length} places` : `${shown.length} of ${all.length} places`}
		</span>
	</div>
	{#if !shown.length}
		<p class="muted empty">No places match these filters.</p>
	{:else if view === 'map'}
		<div class="body"><PlacesMap rows={shown} /></div>
	{:else}
		<PlaceTable rows={shown} onfilter={(key, value) => addFilter(key, value)} />
	{/if}
</div>

<style>
	.actions {
		display: flex;
		gap: 8px;
	}
	.tabs {
		display: flex;
		align-items: center;
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
	}
	.body {
		padding: 16px;
	}
	.empty {
		padding: 16px;
		margin: 0;
	}
</style>
