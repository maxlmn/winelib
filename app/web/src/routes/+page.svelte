<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import Change from '#lib/components/Change.svelte';
	import { pct, plural, money } from '#lib/format.ts';
	import WhatToOpen from '#lib/components/home/WhatToOpen.svelte';
	import CellarSection from '#lib/components/details/CellarSection.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import GettingStarted from '#lib/components/home/GettingStarted.svelte';
	import { DEMO } from '#lib/demo.ts';
	import { integrations } from '#lib/settings.svelte.ts';
	import OccasionCard from '#lib/components/tastings/OccasionCard.svelte';
	import TastingRibbon from '#lib/components/tastings/TastingRibbon.svelte';
	import { occasions } from '#lib/components/tastings/journal.ts';
	import { goto } from '$app/navigation';
	import type { Bottle } from '#lib/types.ts';

	let { data } = $props();
	const d = $derived(data.dashboard);
	const gain = $derived(pct(d.cellar.cost, d.cellar.market));
	const year = $derived(d.today.slice(0, 4));

	// The latest evenings, as rows: the last one, and the ones before while they stay short
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
	// The latest tasting: the latest evening's last wine (the home map opens on it). A wine of the latest tastings
	// pointed at (hovered a moment, or tapped) takes its place on the map
	const lastWine = $derived(latest[0]?.wines.at(-1) ?? null);
	// ...as does a bottle of what to open or of the recent purchases: the one shown marked in its list
	type Pointed = { kind: 'tasting' | 'bottle'; id: number; wine_id: number; region: string | null };
	let pointed = $state<Pointed | null>(null);
	let pointTimer: ReturnType<typeof setTimeout> | undefined;
	function point(p: Pointed, wait = 180) {
		clearTimeout(pointTimer);
		// a moment's pause first: a pointer crossing a list doesn't send the map flying from wine to wine
		if (wait) pointTimer = setTimeout(() => (pointed = p), wait);
		else pointed = p;
	}
	const pointTasting = (t: { id: number; wine_id: number; region: string | null }, wait = 180) =>
		point({ kind: 'tasting', id: t.id, wine_id: t.wine_id, region: t.region }, wait);
	// along the year's ribbon: quicker (it's swept along), at once for its replay
	const pointBottle = (b: Bottle) => point({ kind: 'bottle', id: b.bottle_id, wine_id: b.wine_id, region: b.region });
	const shownWine = $derived(pointed ?? (lastWine ? { kind: 'tasting' as const, id: lastWine.id, wine_id: lastWine.wine_id, region: lastWine.region } : null));
	// an evening's place pointed at (its line in the latest tastings): pinned on the map, until a wine is pointed at
	let pinned = $state<[number, number] | null>(null);
	$effect(() => {
		void pointed;
		pinned = null;
	});
	function pointPlace(where: [number, number]) {
		clearTimeout(pointTimer);
		pointTimer = setTimeout(() => (pinned = where), 180);
	}
	const shownTasting = $derived(shownWine?.kind === 'tasting' ? shownWine.id : null);
	const shownBottle = $derived(shownWine?.kind === 'bottle' ? shownWine.id : null);
	// The past year's wines as one line of region colours
	const yearAgo = $derived(`${Number(d.today.slice(0, 4)) - 1}${d.today.slice(4)}`);
	const recentTastings = $derived(data.journal.tastings.filter((t) => t.date >= yearAgo));
	// The last dozen purchases still in the cellar, as lines
	const recentBottles = $derived(
		data.cellar.bottles
			.filter((b) => b.purchase_date)
			.sort((a, b) => b.purchase_date!.localeCompare(a.purchase_date!))
			.slice(0, 12)
	);
	const recentQty = $derived(recentBottles.reduce((n, b) => n + b.qty, 0));

	// A wine at random: any you hold or have tasted, each once however many bottles or notes
	const wineIds = $derived([...new Set([...data.cellar.bottles, ...data.journal.tastings].map((x) => x.wine_id))]);
	const randomWine = () => goto(links.wine(wineIds[Math.floor(Math.random() * wineIds.length)]));

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
		{#if wineIds.length}
			<button class="btn icon" onclick={randomWine} title="A wine at random" aria-label="A wine at random"><Icon name="dice" size={15} /></button>
		{/if}
	</div>
</div>

<!-- A new installation: what to do first, while the cellar and the journal are empty or the maps have no outlines
     (not in the demo) -->
{#if !DEMO && ((!data.cellar.bottles.length && !data.journal.tastings.length) || !integrations.outlines)}
	<GettingStarted bottles={data.cellar.bottles.length} tastings={data.journal.tastings.length} />
{/if}

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

<!-- The map is the page's ground: the whole window behind the cards, on the latest tasting's wine (or the one
     pointed at in the list) -->
<HomeMap full focus={pinned ? { point: pinned } : shownWine ? { wineId: shownWine.wine_id, region: shownWine.region } : null} />

<section class="card latest">
	<div class="sec-head">
		<h2>Latest {latest.length > 1 ? 'tastings' : 'tasting'}</h2>
		<a class="more" href={links.tastings()}>All tasting notes →</a>
	</div>
	{#each latest as o (o.key)}
		<OccasionCard occasion={o} regionColors={data.regionColors} plain onwine={pointTasting} shown={pinned ? null : shownTasting} onplace={pointPlace} />
	{:else}
		<p class="muted">No tastings yet. <a class="more" href={links.newTasting()}>Add the first one</a></p>
	{/each}
</section>
{#if recentTastings.length > 1}
	<TastingRibbon
		tastings={recentTastings}
		label="The past year, a wine per bar: its region’s colour (its own below). Sweep it, or replay it, the map following"
		onwine={(t, now) => pointTasting(t, now ? 0 : 90)}
		shown={shownTasting}
	/>
{/if}

<WhatToOpen bottles={data.cellar.bottles} totals={d.drink_soon.bottles} onwine={pointBottle} shown={shownBottle} />
<!-- Without any purchase dates (none recorded), there's nothing recent to show -->
{#if recentBottles.length || !data.cellar.bottles.length}
	<section class="card purchases-card">
		<div class="sec-head">
			<h2>Recent purchases <span class="muted num">{plural(recentQty, 'bottle')}</span></h2>
			<a class="more" href={links.cellar()}>The cellar →</a>
		</div>
		{#if recentBottles.length}
			<CellarSection bottles={recentBottles} regionColors={data.regionColors} prices onwine={pointBottle} shown={shownBottle} />
		{:else}
			<p class="muted">No purchases yet. <a class="more" href={links.newBottle()}>Add one</a></p>
		{/if}
	</section>
{/if}

<style>
	/* over the map, on a card of its own (app.css: html.map-full main > .page-head) */
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
	.latest :global(.occ) {
		margin: 0;
		padding: 10px 0;
	}
	.latest :global(.occ + .occ) {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.latest :global(.occ:last-child) {
		padding-bottom: 0;
	}
	.purchases-card h2 .muted {
		font-weight: 400;
		font-size: 13px;
		margin-left: 6px;
	}
</style>
