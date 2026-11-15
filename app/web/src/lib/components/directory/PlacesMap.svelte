<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import type { PlaceRow } from '#lib/api/directory.ts';
	import PointMap from '#lib/components/PointMap.svelte';
	import type { MapPoint } from '#lib/components/PointMap.svelte';
	import { plural } from '#lib/format.ts';
	import { links } from '#lib/links.ts';
	import { accentColor } from '#lib/theme.svelte.ts';
	import Stars from './Stars.svelte';
	import { portal } from '#lib/portal.ts';

	/** full: the whole window behind the page (html.map-full in app.css), the page's column over its left side (its
	 * lower half on a phone); `selectedId` chosen here or in the page's list (bindable), flown to */
	let { rows, full = false, selectedId = $bindable(null) }: { rows: PlaceRow[]; full?: boolean; selectedId?: number | null } = $props();

	const NOT_VISITED = '#9a93a0';

	$effect(() => {
		document.documentElement.classList.toggle('map-full', full);
		return () => document.documentElement.classList.remove('map-full');
	});
	let winWidth = $state(1024);
	let winHeight = $state(768);
	const phone = $derived(winWidth <= 760);

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

<svelte:window bind:innerWidth={winWidth} bind:innerHeight={winHeight} />

<div class="map" class:full use:portal={full}>
	<PointMap
		{points}
		{selectedId}
		onselect={(id) => (selectedId = id)}
		zoom={13}
		flyToSelected={full}
		padLeft={full && !phone ? 560 : 0}
		padBottom={full && phone ? Math.round(winHeight * 0.45) : 0}
	/>
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
				<a class="btn icon" href={links.newVisit({ place_id: selected.id })} title="Add a visit here" aria-label="Add a visit here"><span class="plus">+</span><Icon name="pin" size={15} /></a>
			</div>
		</div>
	{/if}
</div>
<div class="legend muted" class:over={full}>
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
	/* Full size: behind the page's column, beside the sidebar; under the bar and over the tab bar on a phone */
	.map.full {
		position: fixed;
		inset: 0 0 0 200px;
		z-index: 40;
		height: auto;
		min-height: 0;
		border-radius: 0;
	}
	@media (max-width: 760px) {
		.map.full {
			inset: var(--nav-h, 52px) 0 var(--tab-h, 0px) 0;
		}
	}
	/* full size, the legend under the page's other cards: in the column, a card of its own */
	.legend.over {
		padding: 8px 12px;
		margin-bottom: 14px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow);
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
