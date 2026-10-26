<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Place, Tasting } from '#lib/api/tastings.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { links } from '#lib/links.ts';
	import ShowMore from './ShowMore.svelte';

	let { tastings, places, regionColors }: { tastings: Tasting[]; places: Record<string, Place>; regionColors: RegionColors } = $props();

	type Key = keyof Tasting;
	const cols = $derived<{ key: Key; label: string; num?: boolean }[]>([
		{ key: 'date', label: 'Date' },
		{ key: 'seq', label: 'Seq', num: true },
		{ key: 'color', label: '' },
		{ key: 'region', label: 'Region' },
		{ key: 'producer', label: 'Producer' },
		{ key: 'cuvee', label: 'Cuvée' },
		{ key: 'appellation', label: 'Appellation' },
		{ key: 'varietal', label: 'Grapes' },
		{ key: 'vintage', label: 'Vintage' },
		{ key: 'format', label: 'Format' },
		{ key: 'glasses', label: 'Glasses', num: true },
		{ key: 'location', label: 'Location' },
		{ key: 'score', label: 'Scores', num: true }
	]);

	const STEP = 150;
	let limit = $state(STEP);
	let sortKey = $state<Key>('date');
	let asc = $state(false);

	function sortBy(key: Key) {
		if (sortKey === key) asc = !asc;
		else [sortKey, asc] = [key, !(key === 'date' || cols.find((c) => c.key === key)?.num)];
		limit = STEP;
	}

	const sorted = $derived.by(() => {
		const dir = asc ? 1 : -1;
		// scores are strings like "95", "17.5" or "(93-95)"
		const val = (t: Tasting) => (sortKey === 'score' ? parseFloat((t.score ?? '').replace(/^\D+/, '')) || null : t[sortKey]);
		return [...tastings].sort((a, b) => {
			const x = val(a), y = val(b);
			if (x === y) return (a.date === b.date ? (a.seq ?? 0) - (b.seq ?? 0) : b.date.localeCompare(a.date));
			if (x === null || x === '') return 1;
			if (y === null || y === '') return -1;
			return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))) * dir;
		});
	});
</script>

<div class="wrap">
	<table>
		<thead>
			<tr>
				{#each cols as c}
					<th class:num={c.num} aria-sort={sortKey === c.key ? (asc ? 'ascending' : 'descending') : 'none'}>
						<button class="sort" onclick={() => sortBy(c.key)}>{c.label}{#if sortKey === c.key}<span class="arrow">{asc ? '↑' : '↓'}</span>{/if}</button>
					</th>
				{/each}
				<th></th>
			</tr>
		</thead>
		<tbody>
			{#each sorted.slice(0, limit) as t (t.id)}
				<tr>
					<td class="tabular"><a href={links.tasting(t.id)} title={t.notes || 'Open the tasting'}>{t.date}</a></td>
					<td class="num muted">{t.seq ?? ''}</td>
					<td class="end">
						<BottleEnd
							region={t.region ? (regionColors[t.region] ?? FALLBACK_REGION) : null}
							color={t.color}
							format={t.format}
							size={12}
							title="{regionLabel(t.region)} · {t.color ?? ''}{t.format ? ` · ${t.format}` : ''}"
						/>
					</td>
					<td>{#if t.region}<a class="region" href={links.region(t.region)}>{regionLabel(t.region)}</a>{/if}</td>
					<td class="strong"><a href={links.producer(t.producer_id)}>{t.producer}</a></td>
					<td><a href={links.wine(t.wine_id)}>{t.cuvee || '—'}</a></td>
					<td class="muted">
						{#if t.appellation_id}<a href={links.appellation(t.appellation_id)}>{t.appellation}</a>{:else}{t.appellation ?? ''}{/if}
					</td>
					<td class="muted">{#each t.grapes as g, i (g)}{#if i}{', '}{/if}<a class="region" href={links.grape(g)}>{g}</a>{/each}</td>
					<td class="strong num">{t.vintage}</td>
					<td class="muted">{t.format ?? ''}</td>
					<td class="num">{t.glasses?.toFixed(1) ?? ''}</td>
					<td>
						{#if t.place_id && places[t.place_id]}<a href={links.place(t.place_id)}><PlaceName name={t.location} type={places[t.place_id].type} /></a>{:else}{t.location}{/if}
					</td>
					<td class="num scores"><CriticPills scores={t.scores} /></td>
					<td><a class="edit" href={links.editTasting(t.id)} title="Edit tasting">✎</a></td>
				</tr>
			{/each}
		</tbody>
	</table>
	<ShowMore shown={Math.min(limit, sorted.length)} total={sorted.length} step={STEP} onmore={() => (limit += STEP)} />
</div>

<style>
	.wrap {
		overflow: auto;
		max-height: 75vh;
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
		cursor: pointer;
		user-select: none;
		white-space: nowrap;
	}
	th:hover {
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
	.tabular {
		font-variant-numeric: tabular-nums;
	}
	.strong {
		font-weight: 600;
	}
	.region {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	td.end {
		width: 1%;
		line-height: 0;
	}
	.edit {
		color: var(--muted);
	}
	a.region {
		color: inherit;
	}
	a.region:hover {
		color: var(--accent);
	}
</style>
