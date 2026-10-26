<script lang="ts">
	import type { PlaceRow } from '#lib/api/directory.ts';
	import PointMap from '#lib/components/PointMap.svelte';
	import type { MapPoint } from '#lib/components/PointMap.svelte';
	import { plural } from '#lib/format.ts';
	import { links } from '#lib/links.ts';
	import { accentColor } from '#lib/theme.svelte.ts';
	import Stars from './Stars.svelte';

	let { rows }: { rows: PlaceRow[] } = $props();

	const NOT_VISITED = '#9a93a0';

	let selectedId = $state<number | null>(null);

	const located = $derived(rows.filter((p) => p.lat !== null && p.lng !== null));
	const points = $derived(
		located.map(
			(p): MapPoint => ({
				id: p.id,
				lat: p.lat!,
				lng: p.lng!,
				label: `${p.name}${p.stars ? ' ' + '★'.repeat(p.stars) : ''}`,
				sub: [[p.city, p.country].filter(Boolean).join(', '), p.visits ? plural(p.visits, 'visit') : 'not visited']
					.filter(Boolean)
					.join(' · '),
				color: p.visits ? accentColor() : NOT_VISITED,
				weight: p.visits + 1
			})
		)
	);
	const selected = $derived(located.find((p) => p.id === selectedId) ?? null);
</script>

<div class="map">
	<PointMap {points} {selectedId} onselect={(id) => (selectedId = id)} zoom={13} />
	{#if selected}
		<div class="pick card">
			<button class="close" onclick={() => (selectedId = null)} aria-label="Close">✕</button>
			<a class="name" href={links.place(selected.id)}>{selected.name}</a>
			<Stars n={selected.stars} />
			<div class="muted">{[selected.type, selected.city, selected.country].filter(Boolean).join(' · ')}</div>
			<div class="num">
				{selected.visits ? `${plural(selected.visits, 'visit')}, last ${selected.last_visit}` : 'Not visited yet'}
			</div>
			<div class="actions">
				<a class="btn" href={links.place(selected.id)}>Open</a>
				<a class="btn" href={links.newVisit({ place_id: selected.id })}>+ Visit</a>
			</div>
		</div>
	{/if}
</div>
<div class="legend muted">
	<span><span class="dot" style:background="var(--accent)"></span> Visited (size: number of visits)</span>
	<span><span class="dot" style:background={NOT_VISITED}></span> Not visited</span>
	<span class="num">{located.length} of {rows.length} places have coordinates</span>
</div>

<style>
	.map {
		position: relative;
		height: 62vh;
		min-height: 360px;
		border-radius: 8px;
		overflow: hidden;
	}
	.pick {
		position: absolute;
		right: 12px;
		top: 12px;
		z-index: 2;
		width: 250px;
		padding: 12px 14px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 13px;
	}
	.name {
		font-weight: 650;
		font-size: 15px;
		padding-right: 18px;
	}
	.close {
		position: absolute;
		right: 8px;
		top: 6px;
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
	}
	.actions {
		display: flex;
		gap: 6px;
		margin-top: 6px;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		margin-top: 10px;
		font-size: 12px;
	}
	.legend > span {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}
	.legend .num {
		margin-left: auto;
	}
</style>
