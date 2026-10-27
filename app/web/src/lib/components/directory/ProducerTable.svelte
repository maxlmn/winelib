<script lang="ts">
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { ProducerRow } from '#lib/api/directory.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import Sentinel from './Sentinel.svelte';
	import { sortRows } from './facets.ts';

	interface Props {
		rows: ProducerRow[];
		/** clicking a region, sub-region, village or list filters on it */
		onfilter: (key: 'region' | 'subregion' | 'village' | 'list', value: string) => void;
	}

	let { rows, onfilter }: Props = $props();

	const PAGE = 100;
	type Key = 'name' | 'region' | 'subregion' | 'village' | 'winemaker' | 'tastings' | 'bottles';
	const cols: { key: Key | null; label: string; num?: boolean }[] = [
		{ key: 'name', label: 'Name' },
		{ key: 'region', label: 'Region' },
		{ key: 'subregion', label: 'Sub-region' },
		{ key: 'village', label: 'Village' },
		{ key: 'winemaker', label: 'Winemaker' },
		{ key: 'tastings', label: 'Tasted', num: true },
		{ key: 'bottles', label: 'Cellar', num: true },
		{ key: null, label: 'Lists' },
		{ key: null, label: 'Notes' }
	];

	// null: the API's order (region, sub-region, village, name)
	let sortKey = $state<Key | null>(null);
	let asc = $state(true);
	let limit = $state(PAGE);
	let wrap = $state<HTMLDivElement>();

	function sortBy(key: Key) {
		if (sortKey === key) asc = !asc;
		else [sortKey, asc] = [key, !cols.find((c) => c.key === key)?.num];
	}

	const sorted = $derived(sortKey ? sortRows(rows, (r) => r[sortKey!], asc) : rows);

	$effect(() => {
		void sorted;
		limit = PAGE;
		wrap?.scrollTo({ top: 0 });
	});
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
				<tr style:--rc={p.region ? (p.color ?? FALLBACK_REGION) : 'transparent'}>
					<td class="strong"><a href={links.producer(p.id)}>{p.name}</a></td>
					<td>
						{#if p.region}
							<button class="cell region" onclick={() => onfilter('region', p.region!)} title="Filter by {regionLabel(p.region)}">
								{regionLabel(p.region)}
							</button>
							<a class="to-region" href={links.region(p.region)} title="{regionLabel(p.region)}: region page">↗</a>
						{/if}
					</td>
					<td class="clip" title={p.subregion}>{#if p.subregion}<button class="cell" onclick={() => onfilter('subregion', p.subregion!)}>{p.subregion}</button>{/if}</td>
					<td class="clip" title={p.village}>{#if p.village}<button class="cell" onclick={() => onfilter('village', p.village!)}>{p.village}</button>{/if}</td>
					<td class="clip" title={p.winemaker}>{p.winemaker ?? ''}</td>
					<td class="num">{p.tastings || ''}</td>
					<td class="num">{p.bottles || ''}</td>
					<td class="lists">
						{#each p.list_refs as l (l.id)}<span class="list-ref"><button class="tag" onclick={() => onfilter('list', l.name)} title="Filter by {l.name}">{l.name}</button><a class="to-region" href={links.list(l.id)} title="{l.name}: the list">↗</a></span>{/each}
					</td>
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
	}
	.cell:hover {
		color: var(--accent);
	}
	/* The region in its color: a bar down the row's edge, and the region as a tinted pill */
	tr td:first-child {
		box-shadow: inset 4px 0 0 var(--rc);
		padding-left: 14px;
	}
	.region {
		display: inline-flex;
		align-items: center;
		padding: 1px 9px;
		border-radius: 10px;
		background: color-mix(in srgb, var(--rc) 30%, transparent);
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--rc) 60%, transparent);
	}
	.region:hover {
		background: color-mix(in srgb, var(--rc) 45%, transparent);
		color: var(--text);
	}
	.lists {
		white-space: normal;
		min-width: 140px;
	}
	.tag {
		display: inline-block;
		margin: 1px 4px 1px 0;
		padding: 1px 7px;
		border: none;
		border-radius: 4px;
		background: var(--surface-2);
		font-size: 11px;
		cursor: pointer;
		white-space: nowrap;
	}
	.tag:hover {
		background: var(--accent-soft);
		color: var(--accent);
	}
	.clip {
		max-width: 170px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.notes {
		max-width: 220px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.list-ref {
		display: inline-flex;
		align-items: baseline;
		margin-right: 6px;
		white-space: nowrap;
	}
	.to-region {
		margin-left: 4px;
		font-size: 11px;
		color: var(--muted);
		text-decoration: none;
	}
	.to-region:hover {
		color: var(--accent);
	}
</style>
