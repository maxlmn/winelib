<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import Change from '#lib/components/Change.svelte';
	import { pct, plural, money } from '#lib/format.ts';
	import WhatToOpen from '#lib/components/home/WhatToOpen.svelte';
	import CellarCards from '#lib/components/CellarCards.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import OccasionCard from '#lib/components/tastings/OccasionCard.svelte';
	import TastingRibbon from '#lib/components/tastings/TastingRibbon.svelte';
	import { occasions } from '#lib/components/tastings/journal.ts';

	let { data } = $props();
	const d = $derived(data.dashboard);
	const gain = $derived(pct(d.cellar.cost, d.cellar.market));
	const year = $derived(d.today.slice(0, 4));

	// The latest evenings, as cards of the tasting journal: the last one, and the ones before while they stay short
	// (about 8 wines in all)
	const latest = $derived.by(() => {
		const out = [];
		let wines = 0;
		for (const o of occasions(data.journal, data.journal.tastings, [])) {
			if (!o.wines.length) continue;
			if (out.length && wines + o.wines.length > 8) break;
			out.push(o);
			wines += o.wines.length;
			if (out.length === 3) break;
		}
		return out;
	});
	// The past year's wines as one line of region colours
	const yearAgo = $derived(`${Number(d.today.slice(0, 4)) - 1}${d.today.slice(4)}`);
	const recentTastings = $derived(data.journal.tastings.filter((t) => t.date >= yearAgo));
	// The last dozen purchases still in the cellar, as the cellar's cards
	const recentBottles = $derived(
		data.cellar.bottles
			.filter((b) => b.purchase_date)
			.sort((a, b) => b.purchase_date!.localeCompare(a.purchase_date!))
			.slice(0, 12)
	);
	const recentQty = $derived(recentBottles.reduce((n, b) => n + b.qty, 0));

	const greeting = (() => {
		const h = new Date().getHours();
		return h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
	})();

</script>

<svelte:head><title>Home · WineLib</title></svelte:head>

<div class="page-head">
	<div>
		<h1>{greeting}</h1>
		<p class="muted date">{fmtDate(d.today)}</p>
	</div>
	<div class="actions">
		<a class="btn icon primary" href={links.newTasting()} title="Add a tasting" aria-label="Add a tasting"><span class="plus">+</span><Icon name="glass" size={15} /></a>
		<a class="btn icon primary" href={links.newBottle()} title="Add a purchase" aria-label="Add a purchase"><span class="plus">+</span><Icon name="bottle" size={15} /></a>
		<a class="btn icon" href={links.newVisit()} title="Add a restaurant visit" aria-label="Add a restaurant visit"><span class="plus">+</span><Icon name="pin" size={15} /></a>
	</div>
</div>

<div class="kpis">
	<a class="kpi card" href={links.cellar()}>
		<div class="label">Bottles in cellar</div>
		<div class="value num">{d.cellar.bottles}</div>
	</a>
	<a class="kpi card" href={links.cellar({ view: 'prices' })}>
		<div class="label">Market value</div>
		<div class="value num">{d.cellar.market ? money(d.cellar.market) : '–'}</div>
		{#if d.cellar.market}<div class="sub num"><Change value={gain} digits={1} /> on cost</div>{/if}
	</a>
	<a class="kpi card" href={links.tastings()}>
		<div class="label">Wines tasted in {year}</div>
		<div class="value num">{d.year.tastings}</div>
	</a>
	<a class="kpi card" href={links.cellar({ view: 'list' })}>
		<div class="label">Purchases in {year}</div>
		<div class="value num">{d.year.purchases}</div>
	</a>
</div>

<!-- Two rows, their columns as tall as each other: the map beside the latest tasting and the year's wines; what to
     open beside what came in, half and half -->
<div class="row">
	<section class="card map-card">
		<div class="sec-head">
			<h2>Your wine map</h2>
			<a class="more" href={links.map()}>The map →</a>
		</div>
		<HomeMap focus={latest[0]?.wines[0]?.region ?? null} />
	</section>
	<div class="side">
		<section class="latest">
			<div class="sec-head">
				<h2>Latest {latest.length > 1 ? 'tastings' : 'tasting'}</h2>
				<a class="more" href={links.tastings()}>All tasting notes →</a>
			</div>
			{#each latest as o (o.key)}
				<OccasionCard occasion={o} regionColors={data.regionColors} />
			{:else}
				<p class="card muted pad">No tastings yet. <a class="more" href={links.newTasting()}>Add the first one</a></p>
			{/each}
		</section>
		{#if recentTastings.length > 1}
			<TastingRibbon tastings={recentTastings} label="The past year, a wine per bar: its region’s colour (its own below)" />
		{/if}
	</div>
</div>

<div class="row even">
	<WhatToOpen bottles={data.cellar.bottles} totals={d.drink_soon.bottles} />
	<!-- Without any purchase dates (none recorded), there's nothing recent to show -->
	{#if recentBottles.length || !data.cellar.bottles.length}
		<section class="card purchases-card">
			<div class="sec-head">
				<h2>Recent purchases <span class="muted num">{plural(recentQty, 'bottle')}</span></h2>
				<a class="more" href={links.cellar()}>The cellar →</a>
			</div>
			{#if recentBottles.length}
				<CellarCards bottles={recentBottles} regionColors={data.regionColors} prices />
			{:else}
				<p class="muted">No purchases yet. <a class="more" href={links.newBottle()}>Add one</a></p>
			{/if}
		</section>
	{/if}
</div>

<style>
	.page-head {
		align-items: flex-end;
	}
	h1 {
		margin: 0;
	}
	.date {
		margin: 2px 0 0;
		font-size: 13px;
	}
	.actions {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}
	.kpis {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 12px;
		margin-bottom: 14px;
	}
	.kpi {
		padding: 14px 16px;
		color: inherit;
		text-decoration: none;
		transition: border-color 0.15s;
	}
	.kpi:hover {
		border-color: var(--accent);
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.value {
		font-size: 22px;
		font-weight: 650;
	}
	.sub {
		font-size: 12px;
	}
	section.card {
		padding: 16px 18px;
		margin-bottom: 14px;
	}
	h2 {
		font-size: 15px;
		margin: 0;
	}
	.sec-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin-bottom: 8px;
	}
	.more {
		font-size: 13px;
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.more:hover {
		color: var(--accent);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		gap: 14px;
		margin-bottom: 14px;
	}
	.row.even {
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	}
	@media (max-width: 1000px) {
		.row,
		.row.even {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	.side {
		display: flex;
		flex-direction: column;
		gap: 14px;
		min-width: 0;
	}
	.side > :global(*),
	.row > :global(*) {
		margin: 0;
	}
	/* Beside the map: the latest tasting at the top, the year's ribbon at the bottom, level with the map */
	.side > :global(.ribbon) {
		margin-top: auto;
	}
	/* The map grows to its row's height (the latest tasting and the ribbon beside it) */
	.map-card {
		display: flex;
		flex-direction: column;
		padding: 14px 14px 12px;
	}
	.latest .sec-head {
		padding: 4px 4px 0;
	}
	.latest {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.latest :global(.occ) {
		margin: 0;
	}
	.pad {
		padding: 16px 18px;
	}
	.purchases-card h2 .muted {
		font-weight: 400;
		font-size: 13px;
		margin-left: 6px;
	}
</style>
