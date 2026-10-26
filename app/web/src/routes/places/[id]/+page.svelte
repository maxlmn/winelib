<script lang="ts">
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

	let { data } = $props();
	const p = $derived(data.detail);
	const point = $derived(
		p.lat !== null && p.lng !== null
			? [{ id: p.id, lat: p.lat, lng: p.lng, label: `${p.name}${p.michelin_stars ? ` ${stars(p.michelin_stars)}` : ''}`, sub: [p.city, p.country].filter(Boolean).join(', ') }]
			: []
	);
</script>

<svelte:head><title>{p.name} · WineLib</title></svelte:head>

{#snippet title()}
	<PlaceName name={p.name} type={p.type} />{#if p.michelin_stars}<span class="stars" title="{p.michelin_stars} Michelin star{p.michelin_stars > 1 ? 's' : ''}">{stars(p.michelin_stars)}</span>{/if}
{/snippet}

{#snippet actions()}
	<a class="btn" href={links.editPlace(p.id)}>Edit place</a>
	<a class="btn" href={links.newVisit({ place_id: p.id })}>＋ Visit</a>
	<a class="btn primary" href={links.newTasting({ place_id: p.id })}>＋ Tasting</a>
{/snippet}

{#snippet map()}
	<div class="map"><PointMap points={point} basemap={appSettings.map_default_basemap} zoom={15} /></div>
{/snippet}

{#key p.id}
	<DetailHeader kind={['Place', p.type].filter(Boolean).join(' · ')} {title} trail={[p.city, p.country]} {actions} aside={point.length ? map : undefined}>
		<Stats
			items={[
				{ label: 'Visits', value: p.stats.visits },
				{ label: 'Wines tasted', value: p.stats.tastings },
				{ label: 'Michelin stars', value: p.michelin_stars ?? 0 },
				{ label: 'Wine value', value: p.stats.value ? money(p.stats.value) : '–' }
			]}
		/>
		<div class="facts">
			<Facts
				items={[
					{ label: 'City', value: p.city },
					{ label: 'Country', value: p.country },
					{ label: 'Type', value: p.type }
				]}
			/>
		</div>
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
		color: var(--gold);
		margin-left: 8px;
		font-size: 18px;
		vertical-align: middle;
	}
	.map {
		position: relative;
		height: 300px;
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--border);
	}
	.facts {
		margin-top: 16px;
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
</style>
