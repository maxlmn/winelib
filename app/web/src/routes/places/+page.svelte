<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { setParams } from '#lib/url.ts';
	import { page } from '$app/state';
	import type { PlaceRow } from '#lib/api/directory.ts';
	import DirectoryFilters from '#lib/components/directory/DirectoryFilters.svelte';
	import PlaceTable from '#lib/components/directory/PlaceTable.svelte';
	import PlacesMap from '#lib/components/directory/PlacesMap.svelte';
	import { applyFacets, facetOptions, readSelection, textMatch } from '#lib/components/directory/facets.ts';
	import type { Facet } from '#lib/components/directory/facets.ts';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { plural } from '#lib/format.ts';
	import Stars from '#lib/components/directory/Stars.svelte';

	let { data } = $props();

	const starLabel = (n: number) => (n ? `${n} star${n === 1 ? '' : 's'}` : 'No star');

	const FACETS: Facet<PlaceRow>[] = [
		{ key: 'country', label: 'Country', values: (p) => [p.country] },
		{ key: 'city', label: 'City', values: (p) => [p.city] },
		{ key: 'type', label: 'Type', values: (p) => [p.type] },
		{ key: 'stars', label: 'Michelin', values: (p) => [starLabel(p.stars)] }
	];
	// Two modes: the places over their map (the default), or the table, the page's whole width (view=list)

	const all = $derived(data.places);
	const params = $derived(page.url.searchParams);
	const q = $derived(params.get('q') ?? '');
	const visited = $derived(params.get('visited') === '1');
	const onMap = $derived(params.get('view') !== 'list');
	// a place chosen in the column's list or on the map: the map flies to it, its card open there
	let selectedId = $state<number | null>(null);
	let pointTimer: ReturnType<typeof setTimeout> | undefined;
	function point(id: number, wait = 0) {
		clearTimeout(pointTimer);
		if (wait) pointTimer = setTimeout(() => (selectedId = id), wait);
		else selectedId = id;
	}
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
		<div class="mode" role="group" aria-label="How the places are shown">
			<button class:on={onMap} aria-pressed={onMap} onclick={() => setParams({ view: null })} title="Your places as a list, over their map">On the map</button>
			<button class:on={!onMap} aria-pressed={!onMap} onclick={() => setParams({ view: 'list' })} title="The table, the page's whole width">Tables</button>
		</div>
		<a class="btn icon primary" href={links.newVisit()} title="Add a visit" aria-label="Add a visit"><span class="plus">+</span><Icon name="pin" size={15} /></a>
		<a class="btn icon" href={links.newPlace()} title="Add a place" aria-label="Add a place"><span class="plus">+</span><Icon name="home" size={15} /></a>
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

{#if onMap}
	<PlacesMap rows={shown} full bind:selectedId />
{/if}

<div class="panel card">
	<div class="tabs">
		<h2>{onMap ? 'Places' : 'Table'}</h2>
		<span class="count muted num">
			{shown.length === all.length ? `${all.length} places` : `${shown.length} of ${all.length} places`}
		</span>
	</div>
	{#if !shown.length}
		<p class="muted empty">No places match these filters.</p>
	{:else if onMap}
		<!-- a place a line: clicked (or hovered, Settings › Map) the map flies to it -->
		<ul class="places">
			{#each shown as p (p.id)}
				<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
				<li
					class:shown={selectedId === p.id}
					class:unlocated={p.lat === null || p.lng === null}
					onpointerenter={(e) => e.pointerType === 'mouse' && appSettings.map_follow === 'hover' && p.lat !== null && point(p.id, 180)}
					onclick={(e) => !(e.target as HTMLElement).closest('a, button') && p.lat !== null && point(p.id)}
				>
					<div class="p-main">
						<a href={links.place(p.id)}>{p.name}</a>
						<Stars n={p.stars} />
						<div class="muted p-sub">{[p.type, p.city, p.country].filter(Boolean).join(' · ')}</div>
					</div>
					<div class="muted num p-visits">{p.visits ? plural(p.visits, 'visit') : 'not visited'}</div>
				</li>
			{/each}
		</ul>
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
	.count {
		margin-left: auto;
		font-size: 12px;
	}
	.empty {
		padding: 16px;
		margin: 0;
	}
	.tabs h2 {
		margin: 0;
		padding: 4px 6px 8px;
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
	/* the places in the column: a line each, the one on the map tinted */
	.places {
		list-style: none;
		margin: 0;
		padding: 6px 8px 10px;
	}
	.places li {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 7px 8px;
		border-radius: 6px;
		font-size: 13px;
		cursor: pointer;
		transition: background 0.15s;
	}
	.places li + li {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.places li:hover {
		background: color-mix(in srgb, var(--accent) 5%, transparent);
	}
	.places li.shown {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}
	/* no coordinates: not on the map */
	.places li.unlocated {
		cursor: default;
	}
	.p-main {
		flex: 1;
		min-width: 0;
	}
	.p-sub {
		font-size: 12px;
	}
	.p-visits {
		flex: none;
		font-size: 12px;
	}
</style>
