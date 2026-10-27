<script lang="ts">
	import { shapesUrl } from '#lib/api/details.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import ListsPanel from '#lib/components/details/ListsPanel.svelte';
	import DetailMap from '#lib/components/details/DetailMap.svelte';
	import Facts from '#lib/components/details/Facts.svelte';
	import Stats from '#lib/components/details/Stats.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import WineCatalog from '#lib/components/details/WineCatalog.svelte';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';

	let { data } = $props();
	const p = $derived(data.detail);

	// Next to the map: top appellations by tastings, bottles in the cellar or number of wines, and the vineyards
	type By = 'tastings' | 'bottles' | 'wines';
	let chosenBy = $state<By | null>(null);
	const topBy = $derived<By>(chosenBy ?? (p.stats.tastings ? 'tastings' : p.stats.bottles ? 'bottles' : 'wines'));
	const TOP = 8;
	const topApps = $derived(
		p.appellations
			.filter((a) => a[topBy] > 0)
			.sort((a, b) => b[topBy] - a[topBy] || a.name.localeCompare(b.name))
			.slice(0, TOP)
	);
	const vineyards = $derived(p.vineyards.toSorted((a, b) => a.name.localeCompare(b.name)));
</script>

<svelte:head><title>{p.name} · WineLib</title></svelte:head>

{#snippet actions()}
	<a class="btn" href={links.editProducer(p.id)}>Edit producer</a>
	<a class="btn" href={links.newWine({ producer_id: p.id })}>＋ Wine</a>
{/snippet}

{#snippet stats()}
	<Stats
		items={[
			{ label: 'Bottles in cellar', value: p.stats.bottles, sub: p.stats.value ? money(p.stats.value) : undefined, gold: p.stats.bottles > 0 },
			{ label: 'Wines tasted', value: p.stats.tastings },
			{ label: 'Wines', value: p.stats.wines }
		]}
	/>
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
		<Facts
			items={[
				{ label: 'Also known as', value: p.aliases },
				{ label: 'Winemaker', value: p.winemaker },
				{ label: 'Owner', value: p.owner },
				{ label: 'Importers', value: p.importers }
			]}
		/>
		{#if p.lists.length}
			<div class="block">
				<div class="caption">Lists</div>
				<div class="chips">{#each p.lists as l (l)}<span class="chip">{l}</span>{/each}</div>
			</div>
		{/if}
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
		<section class="card map-card">
			<div class="map-col">
				<h2>Where the wines come from</h2>
				<DetailMap src={shapesUrl('producers', p.id)} height={340} focusable empty="No boundary data for these appellations." />
			</div>
			<aside class="side">
				{#if p.appellations.length}
					<div class="side-head">
						<h3>Top appellations</h3>
						<div class="seg" role="group" aria-label="Rank by">
							{#each [['tastings', 'Tastings'], ['bottles', 'Cellar'], ['wines', 'Wines']] as [id, label] (id)}
								<button class:on={topBy === id} onclick={() => (chosenBy = id as By)}>{label}</button>
							{/each}
						</div>
					</div>
					{#if topApps.length}
						{@const max = topApps[0][topBy]}
						<ol class="top">
							{#each topApps as a (a.id)}
								<li>
									<a href={links.appellation(a.id)}>{a.name}</a>
									<span class="bar" class:gold={topBy === 'bottles'} class:grey={topBy === 'wines'} style:width="{(a[topBy] / max) * 100}%"></span>
									<span class="num count">{a[topBy]}</span>
								</li>
							{/each}
						</ol>
					{:else}
						<p class="muted small">{topBy === 'tastings' ? 'No tastings yet.' : 'No bottles in the cellar.'}</p>
					{/if}
				{/if}
				{#if vineyards.length}
					<h3 class="vine-head">Vineyards <span class="muted num">{vineyards.length}</span></h3>
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
			</aside>
		</section>
	{/if}

	<ListsPanel producerId={p.id} />

	<Tabs
		tabs={[
			{ id: 'cellar', label: 'Cellar', count: p.stats.bottles },
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
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.chip {
		padding: 2px 10px;
		border-radius: 12px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		font-size: 12px;
	}
	.map-card {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 340px;
		gap: 20px;
		padding: 14px 18px;
		margin-bottom: 14px;
	}
	.map-col {
		min-width: 0;
	}
	.side {
		display: flex;
		flex-direction: column;
		min-width: 0;
		max-height: 380px;
	}
	.side-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 8px;
	}
	h3 {
		font-size: 13px;
		margin: 0;
	}
	.vine-head {
		margin: 14px 0 6px;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
		font-size: 11px;
	}
	.seg button {
		padding: 3px 9px;
	}
	.top {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.top li {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr) 2.2em;
		align-items: center;
		gap: 8px;
		padding: 2px 0;
		font-size: 13px;
	}
	.top a,
	.vines a {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.top a:hover,
	.vines a:hover {
		color: var(--accent);
	}
	.bar {
		height: 8px;
		min-width: 3px;
		border-radius: 4px;
		background: var(--accent);
		opacity: 0.75;
	}
	.bar.gold {
		background: var(--gold);
	}
	.bar.grey {
		background: var(--muted);
	}
	.count {
		text-align: right;
		color: var(--muted);
		font-size: 12px;
	}
	.vines {
		list-style: none;
		margin: 0;
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
	.small {
		font-size: 12px;
		margin: 0;
	}
	@media (max-width: 860px) {
		.map-card {
			grid-template-columns: minmax(0, 1fr);
		}
		.side {
			max-height: none;
		}
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
