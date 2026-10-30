<script lang="ts">
	import { shapesUrl } from '#lib/api/details.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import ListsPanel from '#lib/components/details/ListsPanel.svelte';
	import DetailMap from '#lib/components/details/DetailMap.svelte';
	import Facts from '#lib/components/details/Facts.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import WineCatalog from '#lib/components/details/WineCatalog.svelte';
	import { links } from '#lib/links.ts';
	import Icon from '#lib/components/Icon.svelte';
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import { money } from '#lib/format.ts';
	import { mapView } from '#lib/mapView.svelte.ts';

	let { data } = $props();
	// Add to a list (the header's icon): the lists card's form, shown even when it's on none yet
	let addingToList = $state(false);
	const p = $derived(data.detail);

	// The map's legend: the producer's tastings and bottles by appellation and vineyard (the map's own figures are the
	// whole cellar's); its vineyards listed only when the map has nothing to draw
	const mapCounts = $derived(
		Object.fromEntries([
			...p.appellations.map((a) => [`appellation:${a.id}`, a] as const),
			...p.vineyards.map((v) => [`vineyard:${v.id}`, v] as const)
		])
	);
	let mapEmpty = $state(false);
	const vineyards = $derived(p.vineyards.toSorted((a, b) => a.name.localeCompare(b.name)));
</script>

<svelte:head><title>{p.name} · WineLib</title></svelte:head>

{#snippet actions()}
	<ActionMenu>
		<button class="menu-item" role="menuitem" onclick={() => (addingToList = true)}><Icon name="list" size={15} />Add to a list</button>
		<hr />
		<a class="menu-item" role="menuitem" href={links.editProducer(p.id)}><Icon name="edit" size={15} />Edit producer</a>
	</ActionMenu>
	<a class="btn icon primary" href={links.newWine({ producer_id: p.id })} title="Add a wine" aria-label="Add a wine"><span class="plus">+</span><Icon name="bottle" size={15} /></a>
{/snippet}

{#snippet stats()}
	{#if p.website || p.profile_url}
		<div class="ext">
			{#if p.website}<a class="btn" href={p.website} target="_blank" rel="noreferrer">Website ↗</a>{/if}
			{#if p.profile_url}<a class="btn" href={p.profile_url} target="_blank" rel="noreferrer">Profile ↗</a>{/if}
		</div>
	{/if}
{/snippet}

{#key p.id}
	<DetailHeader
		kind={['Producer', p.type].filter(Boolean).join(' · ')}
		icon="person"
		title={p.name}
		trail={[p.region, p.subregion, p.village]}
		regionColor={p.region_color}
		regionHref={p.region ? links.region(p.region) : null}
		{actions}
		aside={stats}
	>
		<ListsPanel inline producerId={p.id} bind:adding={addingToList} />
		<Facts
			items={[
				{ label: 'Also known as', value: p.aliases },
				{ label: 'Winemaker', value: p.winemaker },
				{ label: 'Owner', value: p.owner },
				{ label: 'Importers', value: p.importers }
			]}
		/>
		{#if p.description}
			<div class="block">
				<div class="caption">Description</div>
				<p>{p.description}</p>
			</div>
		{/if}
		{#if p.notes}
			<div class="block note">
				<div class="caption">Notes</div>
				<p>{p.notes}</p>
			</div>
		{/if}
	</DetailHeader>

	{#if p.appellations.length || p.vineyards.length}
		<!-- full size, the map is out behind the page (portal): its card, left with its title, hidden -->
		<section class="card map-card" class:away={mapView.full && !mapEmpty}>
			<h2>Where the wines come from</h2>
			<DetailMap src={shapesUrl('producers', p.id)} height={340} empty="No boundary data for these appellations." counts={mapCounts} bind:nothing={mapEmpty} />
			{#if mapEmpty && vineyards.length}
				<ul class="vines">
					{#each vineyards as v (v.id)}
						<li>
							<a href={links.vineyard(v.id)}>{v.name}</a>
							{#if v.village}<span class="muted where">{v.village}</span>{/if}
							{#if v.tastings}<span class="badge tasted num" title="{v.tastings} tasting{v.tastings > 1 ? 's' : ''}">✎ {v.tastings}</span>{/if}
							{#if v.bottles}<span class="badge num" title="{v.bottles} bottle{v.bottles > 1 ? 's' : ''} in the cellar">{v.bottles}</span>{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}


	<Tabs
		tabs={[
			{ id: 'cellar', label: 'Cellar', count: p.stats.bottles, note: p.stats.value ? money(p.stats.value) : undefined },
			{ id: 'history', label: 'History', count: p.tastings.length },
			{ id: 'wines', label: 'Wines', count: p.stats.wines }
		]}
		initial={p.stats.bottles ? 'cellar' : p.tastings.length ? 'history' : 'wines'}
	>
		{#snippet children(tab)}
			{#if tab === 'cellar'}
				<CellarSection bottles={p.cellar} regionColors={data.regionColors} empty="No bottles from this producer currently in stock." />
				{#if p.cellar.length}
					<a class="more" href={links.cellar({ producer: p.name })}>Open in the cellar →</a>
				{/if}
			{:else if tab === 'history'}
				<TastingHistory tastings={p.tastings} regionColors={data.regionColors} empty="No tasting notes recorded for this producer yet." />
			{:else}
				<WineCatalog wines={p.wines} />
			{/if}
		{/snippet}
	</Tabs>
{/key}

<style>
	.ext {
		display: flex;
		gap: 8px;
		margin-top: 12px;
	}
	.block {
		margin-top: 14px;
	}
	.caption {
		font-size: 12px;
		color: var(--muted);
		margin-bottom: 4px;
	}
	.block p {
		margin: 0;
		white-space: pre-line;
	}
	.note {
		padding: 10px 14px;
		border-radius: 8px;
		background: var(--accent-soft);
	}
	.map-card {
		padding: 14px 18px;
		margin-bottom: 14px;
	}
	.map-card.away {
		display: none;
	}
	.vines a {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.vines a:hover {
		color: var(--accent);
	}
	.vines {
		list-style: none;
		margin: 10px 0 0;
		padding: 0;
		overflow-y: auto;
		min-height: 0;
	}
	.vines li {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 2px 0;
		font-size: 13px;
	}
	.where {
		font-size: 11px;
		white-space: nowrap;
	}
	.badge {
		font-size: 11px;
		font-weight: 600;
		color: var(--gold);
		box-shadow: inset 0 0 0 1px var(--gold);
		border-radius: 8px;
		padding: 0 6px;
	}
	.badge.tasted {
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	h2 {
		font-size: 14px;
		margin: 0 0 10px;
	}
	.more {
		display: inline-block;
		margin-top: 6px;
		font-size: 13px;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.more:hover {
		color: var(--accent);
	}
</style>
