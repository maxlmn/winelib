<script lang="ts">
	import PlaceName from '#lib/components/PlaceName.svelte';
	import type { PlaceRow } from '#lib/api/directory.ts';
	import { links } from '#lib/links.ts';
	import Sentinel from './Sentinel.svelte';
	import Stars from './Stars.svelte';
	import { sortRows } from './facets.ts';

	interface Props {
		rows: PlaceRow[];
		/** clicking a city, country or type filters on it */
		onfilter: (key: 'city' | 'country' | 'type', value: string) => void;
	}

	let { rows, onfilter }: Props = $props();

	const PAGE = 100;
	type Key = 'name' | 'city' | 'country' | 'type' | 'stars' | 'visits' | 'last_visit';
	const cols: { key: Key | null; label: string; num?: boolean }[] = [
		{ key: 'name', label: 'Name' },
		{ key: 'city', label: 'City' },
		{ key: 'country', label: 'Country' },
		{ key: 'type', label: 'Type' },
		{ key: 'stars', label: 'Michelin' },
		{ key: 'visits', label: 'Visits', num: true },
		{ key: 'last_visit', label: 'Last visit', num: true },
		{ key: null, label: 'Notes' }
	];

	// null: the API's order (most recent visit first)
	let sortKey = $state<Key | null>(null);
	let asc = $state(true);
	let limit = $state(PAGE);
	let wrap = $state<HTMLDivElement>();

	function sortBy(key: Key) {
		if (sortKey === key) asc = !asc;
		else [sortKey, asc] = [key, !(cols.find((c) => c.key === key)?.num || key === 'stars')];
	}

	const sorted = $derived(sortKey ? sortRows(rows, (r) => r[sortKey!], asc) : rows);

	$effect(() => {
		void sorted;
		limit = PAGE;
		wrap?.scrollTo({ top: 0 });
	});

	const date = (iso: string) =>
		new Date(iso + 'T00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

	const visitsTitle = (p: PlaceRow) =>
		`${p.visits} day${p.visits === 1 ? '' : 's'} there · ${p.tastings} tasting note${p.tastings === 1 ? '' : 's'}`;
</script>

<div class="wrap" bind:this={wrap}>
	<table>
		<thead>
			<tr>
				{#each cols as c}
					<th class:num={c.num} class:sortable={c.key} aria-sort={c.key ? (sortKey === c.key ? (asc ? 'ascending' : 'descending') : 'none') : undefined}>
						{#if c.key}<button class="sort" onclick={() => c.key && sortBy(c.key)}>{c.label}{#if sortKey === c.key}<span class="arrow">{asc ? '↑' : '↓'}</span>{/if}</button>{:else}{c.label}{/if}
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each sorted.slice(0, limit) as p (p.id)}
				<tr>
					<td class="strong"><a href={links.place(p.id)}><PlaceName name={p.name} type={p.type} /></a></td>
					<td>{#if p.city}<button class="cell" onclick={() => onfilter('city', p.city!)}>{p.city}</button>{/if}</td>
					<td>{#if p.country}<button class="cell" onclick={() => onfilter('country', p.country!)}>{p.country}</button>{/if}</td>
					<td class="muted">{#if p.type}<button class="cell" onclick={() => onfilter('type', p.type!)}>{p.type}</button>{/if}</td>
					<td><Stars n={p.stars} /></td>
					<td class="num" title={p.visits ? visitsTitle(p) : undefined}>{p.visits || ''}</td>
					<td class="num">{p.last_visit ? date(p.last_visit) : ''}</td>
					<td class="notes muted" title={p.notes ?? ''}>{p.notes ?? ''}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if limit < sorted.length}
		<Sentinel root={wrap} shown={limit} onvisible={() => (limit += PAGE)} />
	{/if}
</div>

<style>
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
		z-index: 1;
		background: var(--surface);
		text-align: left;
		font-weight: 600;
		color: var(--muted);
		padding: 8px 10px;
		border-bottom: 1px solid var(--border);
		user-select: none;
		white-space: nowrap;
	}
	th.sortable {
		cursor: pointer;
	}
	th.sortable:hover {
		color: var(--text);
	}
	.arrow {
		margin-left: 4px;
		color: var(--accent);
	}
	td {
		padding: 7px 10px;
		border-bottom: 1px solid var(--border);
		white-space: nowrap;
	}
	tr:hover td {
		background: var(--surface-2);
	}
	.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.strong {
		font-weight: 600;
	}
	.cell {
		border: none;
		background: none;
		padding: 0;
		cursor: pointer;
		text-align: left;
		color: inherit;
	}
	.cell:hover {
		color: var(--accent);
	}
	.notes {
		max-width: 260px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
