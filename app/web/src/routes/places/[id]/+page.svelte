<script lang="ts">
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import PointMap from '#lib/components/PointMap.svelte';
	import RegionStrip from '#lib/components/RegionStrip.svelte';
	import { sortedByRegion, tastingPips } from '#lib/pips.ts';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import Facts from '#lib/components/details/Facts.svelte';
	import Stats from '#lib/components/details/Stats.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import { stars } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { portal } from '#lib/portal.ts';

	let { data } = $props();
	const p = $derived(data.detail);
	const point = $derived(
		p.lat !== null && p.lng !== null
			? [{ id: p.id, lat: p.lat, lng: p.lng, label: `${p.name}${p.michelin_stars ? ` ${stars(p.michelin_stars)}` : ''}`, sub: [p.city, p.country].filter(Boolean).join(', ') }]
			: []
	);
	// With its coordinates the place is over its map (the whole window behind the page, as a wine's), its streets
	// framed beside the page's column (above the cards on a phone)
	const onMap = $derived(point.length > 0);
	$effect(() => {
		document.documentElement.classList.toggle('map-full', onMap);
		return () => document.documentElement.classList.remove('map-full');
	});
	let winWidth = $state(1024);
	let winHeight = $state(768);
	const phone = $derived(winWidth <= 760);
</script>

<svelte:window bind:innerWidth={winWidth} bind:innerHeight={winHeight} />

{#if onMap}
	<div class="place-map" use:portal role="region" aria-label="The place on its map">
		<PointMap
			points={point}
			basemap={appSettings.map_default_basemap}
			zoom={15}
			padLeft={phone ? 0 : 560}
			padBottom={phone ? Math.round(winHeight * 0.45) : 0}
		/>
	</div>
{/if}

<svelte:head><title>{p.name} · WineLib</title></svelte:head>

{#snippet title()}
	<PlaceName name={p.name} type={p.type} />{#if p.michelin_stars}<span class="stars" title="{p.michelin_stars} Michelin star{p.michelin_stars > 1 ? 's' : ''}">{stars(p.michelin_stars)}</span>{/if}
{/snippet}

{#snippet actions()}
	<ActionMenu>
		<a class="menu-item" role="menuitem" href={links.newVisit({ place_id: p.id })}><Icon name="pin" size={15} />Add a visit (no wine)</a>
		<hr />
		<a class="menu-item" role="menuitem" href={links.editPlace(p.id)}><Icon name="edit" size={15} />Edit place</a>
	</ActionMenu>
	<a class="btn icon primary" href={links.newTasting({ place_id: p.id })} title="Add a tasting here" aria-label="Add a tasting here"><span class="plus">+</span><Icon name="glass" size={15} /></a>
{/snippet}

{#key p.id}
	<DetailHeader kind={['Place', p.type].filter(Boolean).join(' · ')} {title} trail={[p.city, p.country]} {actions}>
		<Stats
			items={[
				{ label: 'Visits', value: p.stats.visits },
				{ label: 'Wines tasted', value: p.stats.tastings },
				{ label: 'Michelin stars', value: p.michelin_stars ?? 0 },
				{ label: 'Wine value', value: p.stats.value ? money(p.stats.value) : '–' }
			]}
		/>
		{#if p.tastings.length}
			<!-- The place's palette: what you drank here, a pip per wine in its region's color -->
			<div class="palette">
				<div class="caption">Wines drunk here</div>
				<RegionStrip pips={sortedByRegion(tastingPips(p.tastings))} height={14} />
			</div>
		{/if}
		{#if p.notes}
			<div class="note">
				<div class="caption">Notes</div>
				<p>{p.notes}</p>
			</div>
		{/if}
	</DetailHeader>

	<section class="card history">
		<h2>History</h2>
		<TastingHistory
			tastings={p.tastings}
			visits={p.visits}
			place={{ id: p.id, name: p.name, city: p.city, country: p.country, michelin_stars: p.michelin_stars }}
			regionColors={data.regionColors}
			empty="No history recorded."
		/>
	</section>
{/key}

<style>
	.stars {
		color: var(--gold-text);
		margin-left: 8px;
		font-size: 18px;
		vertical-align: middle;
	}
	.palette {
		margin-top: 14px;
	}
	.palette .caption {
		font-size: 12px;
		color: var(--muted);
		margin-bottom: 6px;
	}
	.note {
		margin-top: 14px;
		padding: 10px 14px;
		border-radius: 8px;
		background: var(--accent-soft);
	}
	.caption {
		font-size: 12px;
		color: var(--muted);
		margin-bottom: 4px;
	}
	.note p {
		margin: 0;
		white-space: pre-line;
	}
	.history {
		padding: 14px 18px 18px;
	}
	h2 {
		font-size: 14px;
		margin: 0 0 12px;
	}
	/* the place's map, full size: behind the page's column, beside the sidebar; under the bar on a phone */
	.place-map {
		position: fixed;
		inset: 0 0 0 200px;
		z-index: 40;
		background: var(--bg);
	}
	@media (max-width: 760px) {
		.place-map {
			inset: var(--nav-h, 52px) 0 var(--tab-h, 0px) 0;
		}
	}
</style>
