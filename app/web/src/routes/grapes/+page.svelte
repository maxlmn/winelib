<script lang="ts">
	import { setParams } from '#lib/url.ts';
	import { page } from '$app/state';
	import { BERRY_COLORS } from '#lib/api/grapes.ts';
	import type { GrapeRow } from '#lib/api/grapes.ts';
	import Stats from '#lib/components/details/Stats.svelte';
	import GrapeNetwork from '#lib/components/directory/GrapeNetwork.svelte';
	import DirectoryFilters from '#lib/components/directory/DirectoryFilters.svelte';
	import { applyFacets, facetOptions, readSelection, sortRows, textMatch } from '#lib/components/directory/facets.ts';
	import type { Facet } from '#lib/components/directory/facets.ts';
	import { links } from '#lib/links.ts';

	let { data } = $props();
	const all = $derived(data.grapes as GrapeRow[]);

	const FACETS: Facet<GrapeRow>[] = [
		{ key: 'color', label: 'Colour', values: (g) => [g.color], swatch: (v) => BERRY_COLORS[v] },
		{ key: 'origin', label: 'Origin', values: (g) => [g.origin] }
	];
	const HAVE = [
		{ id: '', label: 'All' },
		{ id: 'wines', label: 'In my wines' },
		{ id: 'cellar', label: 'In cellar' },
		{ id: 'tasted', label: 'Tasted' },
		{ id: 'family', label: 'With parents' }
	];
	const COLUMNS: { key: keyof GrapeRow | 'family'; label: string; num?: boolean }[] = [
		{ key: 'name', label: 'Grape' },
		{ key: 'color', label: 'Colour' },
		{ key: 'origin', label: 'Origin' },
		{ key: 'family', label: 'Parents' },
		{ key: 'offspring', label: 'Offspring', num: true },
		{ key: 'wines', label: 'Wines', num: true },
		{ key: 'bottles', label: 'Bottles', num: true },
		{ key: 'tastings', label: 'Tastings', num: true }
	];

	const params = $derived(page.url.searchParams);
	const q = $derived(params.get('q') ?? '');
	const have = $derived(params.get('have') ?? '');
	const selection = $derived(readSelection(params, FACETS));
	const sortKey = $derived(params.get('sort') ?? 'mine');
	const asc = $derived(params.get('dir') === 'asc');
	const view = $derived(params.get('view') === 'network' ? 'network' : 'table');

	const base = $derived(
		all.filter(
			(g) =>
				textMatch(q, g.name, g.aliases, g.origin, g.parents.join(' ')) &&
				(have !== 'wines' || g.wines > 0) &&
				(have !== 'cellar' || g.bottles > 0) &&
				(have !== 'tasted' || g.tastings > 0) &&
				(have !== 'family' || g.parents.length > 0)
		)
	);
	const filtered = $derived(applyFacets(base, FACETS, selection));
	const facets = $derived(FACETS.map((facet) => ({ facet, options: facetOptions(base, FACETS, selection, facet) })));
	// Default: yours first (bottles and tastings, then wines), then by name
	const shown = $derived(
		sortKey === 'mine'
			? [...filtered].sort((a, b) => b.bottles + b.tastings - (a.bottles + a.tastings) || b.wines - a.wines || a.name.localeCompare(b.name))
			: sortRows(filtered, (g) => (sortKey === 'family' ? g.parents.join(', ') || null : ((g[sortKey as keyof GrapeRow] as string | number | null) ?? null)), asc)
	);

	// The network shows what the filters keep (null: everything)
	const shownIds = $derived(filtered.length === all.length ? null : new Set(filtered.map((g) => g.id)));
	const links_known = $derived(filtered.reduce((n, g) => n + g.parents.length, 0)); // the shown grapes' parents

	// The stats: over the whole list
	const stats = $derived([
		{ label: 'Grapes', value: all.length },
		{ label: 'In your wines', value: all.filter((g) => g.wines > 0).length },
		{ label: 'In the cellar', value: all.filter((g) => g.bottles > 0).length, gold: true },
		{ label: 'Tasted', value: all.filter((g) => g.tastings > 0).length },
		{ label: 'With known parents', value: all.filter((g) => g.parents.length).length }
	]);
	const byColour = $derived(
		Object.entries(
			all.reduce<Record<string, number>>((m, g) => ((m[g.color ?? 'Unknown'] = (m[g.color ?? 'Unknown'] ?? 0) + 1), m), {})
		).sort((a, b) => b[1] - a[1])
	);
	function sortBy(key: string, num = false) {
		if (sortKey === key) setParams({ dir: asc ? 'desc' : 'asc' });
		else setParams({ sort: key, dir: num ? 'desc' : 'asc' });
	}
	const clearAll = () => setParams({ q: null, have: null, ...Object.fromEntries(FACETS.map((f) => [f.key, null])) });
</script>

<svelte:head><title>Grapes · WineLib</title></svelte:head>

<div class="page-head">
	<h1>Grapes</h1>
	<div class="colours">
		{#each byColour as [c, n] (c)}
			<button class="colour" class:on={selection.color?.includes(c)} onclick={() => setParams({ color: selection.color?.includes(c) ? [] : [c] })}>
				<span class="swatch" style:background={BERRY_COLORS[c] ?? 'var(--border)'}></span>{c} <span class="muted num">{n}</span>
			</button>
		{/each}
	</div>
</div>

<div class="stats"><Stats items={stats} /></div>

<DirectoryFilters
	{q}
	placeholder="Search a grape, an alias, a country, a parent…"
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
			{shown.length === all.length ? `${all.length} grapes` : `${shown.length} of ${all.length} grapes`}{#if view === 'network'}{` · ${links_known} parent links`}{/if}
		</span>
		<span class="right">
			{#if view === 'table' && sortKey !== 'mine'}<button class="link small" onclick={() => setParams({ sort: null, dir: null })}>Yours first</button>{/if}
			<span class="seg small-seg">
				<button class:on={view === 'table'} onclick={() => setParams({ view: null })}>Table</button>
				<button class:on={view === 'network'} onclick={() => setParams({ view: 'network' })}>Family network</button>
			</span>
		</span>
	</div>
	{#if view === 'network'}
		<GrapeNetwork rows={all} shown={shownIds} />
	{:else if shown.length}
		<div class="wrap">
			<table>
				<thead>
					<tr>
						{#each COLUMNS as c (c.key)}
							<th class:num={c.num} aria-sort={sortKey === c.key ? (asc ? 'ascending' : 'descending') : 'none'}>
								<button class="sort" onclick={() => sortBy(c.key, c.num)}>{c.label}{#if sortKey === c.key}<span class="dir">{asc ? '▲' : '▼'}</span>{/if}</button>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each shown as g (g.id)}
						<tr class:mine={g.bottles + g.tastings > 0}>
							<td class="strong">
								<a href={links.grape(g.id)}>{g.name}</a>
								{#if g.aliases}<span class="muted small aliases" title={g.aliases}>{g.aliases}</span>{/if}
							</td>
							<td>{#if g.color}<span class="swatch" style:background={BERRY_COLORS[g.color]}></span>{g.color}{/if}</td>
							<td>{g.origin ?? ''}</td>
							<td class="muted">{g.parents.join(' × ')}</td>
							<td class="num">{g.offspring || ''}</td>
							<td class="num">{g.wines || ''}</td>
							<td class="num">{g.bottles || ''}</td>
							<td class="num">{g.tastings || ''}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<p class="muted empty">No grapes match these filters.</p>
	{/if}
</div>

<style>
	.colours {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.colour {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		border: 1px solid var(--border);
		background: var(--surface);
		border-radius: 14px;
		padding: 3px 10px;
		font-size: 12px;
		cursor: pointer;
	}
	.colour.on {
		border-color: var(--accent);
	}
	.stats {
		margin-bottom: 16px;
	}
	.swatch {
		display: inline-block;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		margin-right: 6px;
		vertical-align: 0.05em;
	}
	.bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
		padding: 10px 14px;
		border-bottom: 1px solid var(--border);
		font-size: 12px;
	}
	.right {
		display: inline-flex;
		align-items: center;
		gap: 12px;
	}
	.small-seg button {
		padding: 3px 10px;
		font-size: 12px;
	}
	.link {
		border: none;
		background: none;
		color: var(--accent);
		cursor: pointer;
	}
	.wrap {
		overflow: auto;
		max-height: 70vh;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}
	th {
		position: sticky;
		top: 0;
		background: var(--surface);
		text-align: left;
		font-weight: 600;
		color: var(--muted);
		padding: 8px 10px;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
		white-space: nowrap;
		user-select: none;
	}
	th:hover {
		color: var(--text);
	}
	td {
		padding: 6px 10px;
		border-bottom: 1px solid var(--border);
		vertical-align: top;
	}
	.num {
		text-align: right;
	}
	.dir {
		margin-left: 4px;
		font-size: 10px;
	}
	.strong a {
		font-weight: 600;
	}
	.aliases {
		display: block;
		max-width: 320px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	tr.mine td:first-child {
		box-shadow: inset 3px 0 0 var(--accent);
	}
	.empty {
		padding: 16px;
		margin: 0;
	}
</style>
