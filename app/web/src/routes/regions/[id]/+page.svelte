<script lang="ts">
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { shapesUrl } from '#lib/api/details.ts';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import DetailHeader from '#lib/components/details/DetailHeader.svelte';
	import DetailMap from '#lib/components/details/DetailMap.svelte';
	import Tabs from '#lib/components/details/Tabs.svelte';
	import TastingHistory from '#lib/components/details/TastingHistory.svelte';
	import { links } from '#lib/links.ts';
	import { plural, money } from '#lib/format.ts';

	let { data } = $props();
	const r = $derived(data.detail);

	// Appellations and producers: everything recorded, or only where you have bottles or tastings
	let onlyMine = $state(false);
	const mine = (x: { bottles: number; tastings: number }) => x.bottles > 0 || x.tastings > 0;

	/** Appellations by sub-region (those without one last) */
	const appGroups = $derived.by(() => {
		const groups = new Map<string, typeof r.appellations>();
		for (const a of r.appellations) {
			if (onlyMine && !mine(a)) continue;
			const key = a.subregion?.trim() || '';
			groups.set(key, [...(groups.get(key) ?? []), a]);
		}
		return [...groups].sort(([a], [b]) => (!a ? 1 : !b ? -1 : a.localeCompare(b)));
	});
	const producers = $derived(r.producers.filter((p) => !onlyMine || mine(p)));
	const mineCount = $derived({ apps: r.appellations.filter(mine).length, producers: r.producers.filter(mine).length });

	// Top appellations and producers, by your tastings or by bottles in the cellar
	const TOP = 8;
	type By = 'tastings' | 'bottles';
	let chosenBy = $state<By | null>(null);
	const topBy = $derived<By>(chosenBy ?? (r.stats.tastings ? 'tastings' : 'bottles'));
	const top = <T extends { bottles: number; tastings: number; name: string }>(rows: T[]) =>
		rows
			.filter((x) => x[topBy] > 0)
			.sort((a, b) => b[topBy] - a[topBy] || a.name.localeCompare(b.name))
			.slice(0, TOP);
	const topApps = $derived(top(r.appellations));
	const topProducers = $derived(top(r.producers));
	const hasTop = $derived(r.stats.tastings > 0 || r.stats.bottles > 0);
</script>

<svelte:head><title>{r.name} · WineLib</title></svelte:head>

{#snippet actions()}
	{#if r.stats.bottles}
		<ActionMenu>
			<a class="menu-item" role="menuitem" href={links.cellar({ region: r.name })}><Icon name="bottle" size={15} />Its bottles in the cellar</a>
		</ActionMenu>
	{/if}
	<a class="btn icon" href={links.map({ region: r.name })} title="Open on the map" aria-label="Open on the map"><Icon name="map" size={15} /></a>
{/snippet}

{#snippet topList(title: string, rows: { id: number; name: string; bottles: number; tastings: number }[], href: (id: number) => string)}
	<div class="top-list">
		<h3>{title}</h3>
		{#if rows.length}
			{@const max = rows[0][topBy]}
			<ol>
				{#each rows as x (x.id)}
					<li>
						<a href={href(x.id)}>{x.name}</a>
						<span class="bar" class:gold={topBy === 'bottles'} style:width="{(x[topBy] / max) * 100}%"></span>
						<span class="num count">{x[topBy]}</span>
					</li>
				{/each}
			</ol>
		{:else}
			<p class="muted">{topBy === 'tastings' ? 'No tastings yet.' : 'No bottles in the cellar.'}</p>
		{/if}
	</div>
{/snippet}

{#snippet badges(x: { bottles: number; tastings: number })}
	{#if x.tastings}<span class="badge tasted num" title={plural(x.tastings, 'tasting')}>✎ {x.tastings}</span>{/if}
	{#if x.bottles}<span class="badge num" title="{plural(x.bottles, 'bottle')} in the cellar">{x.bottles}</span>{/if}
{/snippet}

{#key r.id}
<!-- The page takes the region's color as its accent: each region its own room -->
<div class:tinted={!!r.color} style:--tint={r.color || null}>
	<DetailHeader icon="globe" kind={r.country && r.country !== r.name ? `Wine region · ${r.country}` : 'Wine region'} title={r.name} regionColor={r.color} {actions} />

	<!-- The map draws the region and only the top appellations listed beside it -->
	<section class="card top">
		<div class="map-col">
			<DetailMap
				src={`${shapesUrl('regions', r.id)}?top=${topBy}`}
				height={380}

				empty="No outline for this region yet."
			/>
		</div>
		<aside class="side">
			<div class="top-head">
				<h2>Top</h2>
				{#if hasTop}
					<div class="seg" role="group" aria-label="Rank by">
						<button class:on={topBy === 'tastings'} onclick={() => (chosenBy = 'tastings')}>Drank</button>
						<button class:on={topBy === 'bottles'} onclick={() => (chosenBy = 'bottles')}>Cellar</button>
					</div>
				{/if}
			</div>
			{#if hasTop}
				{@render topList('Appellations', topApps, links.appellation)}
				{@render topList('Producers', topProducers, links.producer)}
			{:else}
				<p class="muted small">No tastings or bottles from this region yet.</p>
			{/if}
		</aside>
	</section>

	<Tabs
		tabs={[
			{ id: 'history', label: 'History', count: r.tastings.length },
			{ id: 'cellar', label: 'Cellar', count: r.stats.bottles, note: r.stats.value ? money(r.stats.value) : undefined },
			{ id: 'appellations', label: 'Appellations', count: r.appellations.length },
			{ id: 'producers', label: 'Producers', count: r.producers.length }
		]}
		initial={r.tastings.length || !r.stats.bottles ? 'history' : 'cellar'}
	>
		{#snippet children(tab)}
			{#if tab === 'history'}
				<TastingHistory tastings={r.tastings} regionColors={data.regionColors} empty="No tastings from this region yet." />
			{:else if tab === 'cellar'}
				<CellarSection bottles={r.cellar} regionColors={data.regionColors} empty="No bottles in the cellar from this region." />
				{#if r.cellar.length}<a class="more" href={links.cellar({ region: r.name })}>Open in the cellar →</a>{/if}
			{:else}
				{@const isApps = tab === 'appellations'}
				<label class="only">
					<input type="checkbox" bind:checked={onlyMine} />
					Only where I have bottles or tastings
					<span class="muted num">({isApps ? mineCount.apps : mineCount.producers})</span>
				</label>
				{#if isApps}
					{#each appGroups as [sub, apps] (sub)}
						<section class="group">
							<h3>{sub || (appGroups.length > 1 ? 'Other' : 'Appellations')} <span class="muted num">{apps.length}</span></h3>
							<ul class="cols">
								{#each apps as a (a.id)}
									<li>
										<a href={links.appellation(a.id)}>{a.name}</a>
										{#if a.type}<span class="muted type">{a.type}</span>{/if}
										{@render badges(a)}
									</li>
								{/each}
							</ul>
						</section>
					{:else}
						<p class="muted">{onlyMine ? 'No appellation with your bottles or tastings.' : 'No appellations recorded for this region.'}</p>
					{/each}
				{:else}
					<ul class="cols">
						{#each producers as p (p.id)}
							<li>
								<a href={links.producer(p.id)}>{p.name}</a>
								{#if p.subregion || p.village}<span class="muted type">{p.village || p.subregion}</span>{/if}
								{@render badges(p)}
							</li>
						{:else}
							<li class="muted">{onlyMine ? 'No producer with your bottles or tastings.' : 'No producers recorded for this region.'}</li>
						{/each}
					</ul>
				{/if}
			{/if}
		{/snippet}
	</Tabs>
</div>
{/key}

<style>
	.top {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 360px;
		gap: 20px;
		padding: 14px 16px;
		margin-bottom: 16px;
	}
	.map-col {
		min-width: 0;
	}
	.side {
		display: flex;
		flex-direction: column;
		gap: 14px;
		min-width: 0;
	}
	.small {
		font-size: 12px;
		margin: 0;
	}
	.top-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}
	.top-head h2 {
		margin: 0;
		font-size: 15px;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
		font-size: 12px;
	}
	.seg button {
		padding: 4px 12px;
	}

	.top-list ol {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.top-list li {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) 2.5em;
		align-items: center;
		gap: 10px;
		padding: 3px 0;
		font-size: 13px;
	}
	.top-list li a {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.top-list li a:hover {
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
	.count {
		text-align: right;
		color: var(--muted);
		font-size: 12px;
	}
	@media (max-width: 860px) {
		.top {
			grid-template-columns: minmax(0, 1fr);
		}
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
	.only {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		margin-bottom: 10px;
	}
	.group + .group {
		margin-top: 14px;
	}
	h3 {
		font-size: 13px;
		margin: 0 0 6px;
		color: var(--muted);
		font-weight: 600;
	}
	.cols {
		list-style: none;
		margin: 0;
		padding: 0;
		columns: 3 240px;
		column-gap: 24px;
	}
	.cols li {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 3px 0;
		break-inside: avoid;
		font-size: 13px;
	}
	.cols a:hover {
		color: var(--accent);
	}
	.type {
		font-size: 11px;
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
</style>
