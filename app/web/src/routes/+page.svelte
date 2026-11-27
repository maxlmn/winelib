<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import { money } from '#lib/format.ts';
	import WhatToOpen from '#lib/components/home/WhatToOpen.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import GettingStarted from '#lib/components/home/GettingStarted.svelte';
	import { DEMO } from '#lib/demo.ts';
	import { integrations } from '#lib/settings.svelte.ts';
	import OccasionCard from '#lib/components/tastings/OccasionCard.svelte';
	import { occasions } from '#lib/components/tastings/journal.ts';
	import { goto } from '$app/navigation';
	import type { Bottle } from '#lib/types.ts';

	let { data } = $props();
	const d = $derived(data.dashboard);
	const year = $derived(d.today.slice(0, 4));

	// The latest evening (the home map opens on its wines' vineyards). A wine of it pointed at (hovered a moment, or
	// tapped) takes its place on the map, as does the bottle suggested
	const evening = $derived(occasions(data.journal, data.journal.tastings, []).find((o) => o.wines.length) ?? null);
	const lastWine = $derived(evening?.wines.at(-1) ?? null);
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
	// the name of what's pointed at, for the map's label
	let pointedName = $state('');
	const named = (w: { producer: string; cuvee?: string | null; vintage?: string | number | null }) =>
		[w.producer, w.cuvee, w.vintage].filter(Boolean).join(' ');
	const pointTasting = (t: { id: number; wine_id: number; region: string | null; producer?: string; cuvee?: string; vintage?: string }, wait = 180) => {
		pointedName = t.producer ? named(t as { producer: string }) : '';
		point({ kind: 'tasting', id: t.id, wine_id: t.wine_id, region: t.region }, wait);
	};
	// along the year's ribbon: quicker (it's swept along), at once for its replay
	const pointBottle = (b: Bottle) => {
		pointedName = named(b);
		point({ kind: 'bottle', id: b.bottle_id, wine_id: b.wine_id, region: b.region });
	};
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
	// What the map shows, and the label over it saying so: the evening (its wines together), one wine of it, the
	// bottle to open, or the place
	const focus = $derived(
		pinned
			? { point: pinned }
			: pointed
				? { wineId: pointed.wine_id, region: pointed.region }
				: lastWine
					? { wineId: lastWine.wine_id, region: lastWine.region, wineIds: [...new Set(evening!.wines.map((w) => w.wine_id))] }
					: null
	);
	// the evening's wines the map frames (HomeMap: all, or the last alone when they lie far apart)
	let framed = $state<number[] | null>(null);
	const eveningLabel = $derived.by(() => {
		if (!evening) return '';
		const ids = [...new Set(evening.wines.map((w) => w.wine_id))];
		const shown = framed?.length ? ids.filter((id) => framed!.includes(id)) : ids;
		if (shown.length === 1) {
			const w = evening.wines.findLast((x) => x.wine_id === shown[0])!;
			return ids.length > 1 ? `${named(w)} (1 of ${ids.length} wines)` : named(w);
		}
		return shown.length < ids.length ? `${shown.length} of ${ids.length} wines` : `${ids.length} wines`;
	});
	const caption = $derived(
		pinned
			? `Where it was opened · ${evening?.name ?? ''}`
			: pointed?.kind === 'bottle'
				? `To open · ${pointedName}`
				: pointed
					? `Tasted · ${pointedName}`
					: evening
						? `Last opened · ${fmtDate(evening.date)}, ${eveningLabel}`
						: null
	);
	const shownBottle = $derived(shownWine?.kind === 'bottle' ? shownWine.id : null);
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
		<p class="stats">
			<a href={links.cellar()}><b class="num">{d.cellar.bottles}</b> bottles</a>
			{#if d.cellar.market}<a href={links.cellar({ view: 'prices' })}><b class="num">{money(d.cellar.market)}</b></a>{/if}
			<a href={links.tastings()}><b class="num">{d.year.tastings}</b> tasted</a>
			<a href={links.cellar({ view: 'list' })}><b class="num">{d.year.purchases}</b> bought in {year}</a>
		</p>
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

<!-- The map is the page: the whole window behind a slim column, on the latest evening's vineyards (or the wine
     pointed at), a label over it saying which -->
<HomeMap full column={400} by="tasted" {focus} {caption} bind:framed />

<section class="card latest">
	<div class="sec-head">
		<h2>Last opened</h2>
		<a class="more" href={links.tastings()}>All tasting notes →</a>
	</div>
	{#if evening}
		<OccasionCard occasion={evening} regionColors={data.regionColors} plain onwine={pointTasting} shown={pinned ? null : shownTasting} onplace={pointPlace} />
	{:else}
		<p class="muted">No tastings yet. <a class="more" href={links.newTasting()}>Add the first one</a></p>
	{/if}
</section>

<WhatToOpen compact bottles={data.cellar.bottles} onwine={pointBottle} shown={shownBottle} />

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
	.stats {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 12px;
		margin: 6px 0 0;
		font-size: 13px;
		color: var(--muted);
	}
	.stats a {
		color: inherit;
		text-decoration: none;
	}
	.stats a:hover {
		color: var(--accent);
	}
	.stats b {
		color: var(--text);
		font-weight: 600;
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
	.latest :global(.occ:last-child) {
		padding-bottom: 0;
	}
</style>
