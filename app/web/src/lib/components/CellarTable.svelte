<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { MATURITY_LABEL, windowLabel } from '#lib/maturity.ts';
	import type { Bottle, RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';

	let { bottles, regionColors }: { bottles: Bottle[]; regionColors: RegionColors } = $props();

	type Col = { key: keyof Bottle; label: string; num?: boolean };
	const cols: Col[] = [
		{ key: 'qty', label: 'Qty', num: true },
		{ key: 'color', label: '' },
		{ key: 'region', label: 'Region' },
		{ key: 'producer', label: 'Producer' },
		{ key: 'cuvee', label: 'Cuvée' },
		{ key: 'appellation', label: 'Appellation' },
		{ key: 'varietal', label: 'Grapes' },
		{ key: 'vintage', label: 'Vintage' },
		{ key: 'format', label: 'Format' },
		{ key: 'location', label: 'Location' },
		{ key: 'purchase_date', label: 'Purchased' },
		{ key: 'price_base', label: 'Paid', num: true },
		{ key: 'market_base', label: 'Market', num: true },
		{ key: 'score', label: 'Scores', num: true },
		{ key: 'drink_to', label: 'Drink', num: true }
	];

	let sortKey = $state<keyof Bottle>('region');
	let asc = $state(true);

	function sortBy(key: keyof Bottle) {
		if (sortKey === key) asc = !asc;
		else [sortKey, asc] = [key, !cols.find((c) => c.key === key)?.num];
	}

	const sorted = $derived.by(() => {
		const dir = asc ? 1 : -1;
		const val = (b: Bottle) => {
			const v = b[sortKey];
			// scores are strings like "95", "17.5" or "(93-95)"
			return sortKey === 'score' ? parseFloat(String(v ?? '').replace(/^\D+/, '')) || -1 : v;
		};
		return [...bottles].sort((a, b) => {
			const x = val(a), y = val(b);
			if (x === y) return a.producer.localeCompare(b.producer);
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
			</tr>
		</thead>
		<tbody>
			{#each sorted as b (b.bottle_id)}
				{@const gain = b.last_price && b.price ? b.market_base - b.price_base : 0}
				<tr>
					<td class="num"><a href={links.bottle(b.bottle_id)} title="Open this bottle">{b.qty}</a></td>
					<td class="end">
						<BottleEnd
							region={regionColors[b.region] ?? FALLBACK_REGION}
							color={b.color}
							format={b.format}
							size={12}
							title="{regionLabel(b.region)} · {b.color ?? ''}{b.format ? ` · ${b.format}` : ''}"
						/>
					</td>
					<td><a class="region quiet" href={links.region(b.region)}>{regionLabel(b.region)}</a></td>
					<td class="strong"><a href={links.producer(b.producer_id)}>{b.producer}</a></td>
					<td><a href={links.wine(b.wine_id)}>{b.cuvee || '—'}</a></td>
					<td class="muted">
						{#if b.appellation_id}<a class="quiet" href={links.appellation(b.appellation_id)}>{b.appellation}</a>{:else}{b.appellation ?? ''}{/if}
					</td>
					<td class="muted">{#each b.grapes as g, i (g)}{#if i}{', '}{/if}<a class="quiet" href={links.grape(g)}>{g}</a>{/each}</td>
					<td class="strong num">{b.vintage}</td>
					<td class="muted">{b.format ?? ''}</td>
					<td><span class="loc">{b.location}</span></td>
					<td class="muted num">{b.purchase_date ?? ''}</td>
					<td class="num">{b.price_base ? money(b.price_base) : ''}</td>
					<td class="num" class:up={gain > 0} class:down={gain < 0}>{b.market_base ? money(b.market_base) : ''}</td>
					<td class="num scores"><CriticPills scores={b.scores} /></td>
					<td class="num drink {b.maturity ?? ''}" title={b.maturity ? MATURITY_LABEL[b.maturity] : ''}>{windowLabel(b.drink_from, b.drink_to)}</td>
				</tr>
			{/each}
		</tbody>
	</table>
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
	.loc {
		padding: 1px 6px;
		border-radius: 4px;
		background: var(--surface-2);
		font-size: 12px;
	}
	.quiet {
		color: inherit;
	}
	.quiet:hover {
		color: var(--accent);
	}
	.up {
		color: var(--up);
	}
	.down {
		color: var(--down);
	}
	.drink.ready {
		color: var(--up);
	}
	.drink.past {
		color: var(--down);
	}
	.drink.young {
		color: var(--muted);
	}
</style>
