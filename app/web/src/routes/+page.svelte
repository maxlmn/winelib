<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import Change from '#lib/components/Change.svelte';
	import { pct, plural, money } from '#lib/format.ts';
	import WhatToOpen from '#lib/components/home/WhatToOpen.svelte';
	import { windowLabel } from '#lib/maturity.ts';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import CellarCards from '#lib/components/CellarCards.svelte';
	import HomeMap from '#lib/components/home/HomeMap.svelte';
	import OccasionCard from '#lib/components/tastings/OccasionCard.svelte';
	import TastingRibbon from '#lib/components/tastings/TastingRibbon.svelte';
	import { occasions } from '#lib/components/tastings/journal.ts';

	let { data } = $props();
	const d = $derived(data.dashboard);
	const gain = $derived(pct(d.cellar.cost, d.cellar.market));
	const year = $derived(d.today.slice(0, 4));

	// The latest evening, as a card of the tasting journal
	const latest = $derived(occasions(data.journal, data.journal.tastings, []).find((o) => o.wines.length) ?? null);
	// The past year's wines as one line of region colours
	const yearAgo = $derived(`${Number(d.today.slice(0, 4)) - 1}${d.today.slice(4)}`);
	const recentTastings = $derived(data.journal.tastings.filter((t) => t.date >= yearAgo));
	// Bottles bought in the last three months still in the cellar, as the cellar's cards (at least the last few)
	const recentBottles = $derived.by(() => {
		const dated = data.cellar.bottles.filter((b) => b.purchase_date).sort((a, b) => b.purchase_date!.localeCompare(a.purchase_date!));
		const since = new Date(Date.parse(d.today) - 92 * 86_400_000).toISOString().slice(0, 10);
		const recent = dated.filter((b) => b.purchase_date! >= since);
		return recent.length >= 6 ? recent : dated.slice(0, 12);
	});
	const recentQty = $derived(recentBottles.reduce((n, b) => n + b.qty, 0));
	// A bottle end per bottle (a mosaic), up to a point
	const MOSAIC = 36;
	const times = (n: number) => Array.from({ length: Math.min(n, MOSAIC) }, (_, i) => i);

	const greeting = (() => {
		const h = new Date().getHours();
		return h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
	})();

	// Without a cuvée name: the appellation and grape instead
	const wineName = (w: { producer: string; cuvee: string; appellation: string | null; varietal: string | null }) => {
		const label = w.cuvee || [w.appellation, w.varietal].filter(Boolean).join(' · ');
		return label ? `${w.producer} – ${label}` : w.producer;
	};
	const since = (iso: string | null) => {
		if (!iso) return 'never opened';
		const years = (Date.parse(d.today) - Date.parse(iso)) / (365.25 * 86_400_000);
		return years >= 2 ? `last opened ${Math.floor(years)} years ago` : 'last opened over a year ago';
	};
</script>

<svelte:head><title>Home · WineLib</title></svelte:head>

<div class="page-head">
	<div>
		<h1>{greeting}</h1>
		<p class="muted date">{fmtDate(d.today)}</p>
	</div>
	<div class="actions">
		<a class="btn primary" href={links.newTasting()}>+ Add tasting</a>
		<a class="btn primary" href={links.newBottle()}>+ Add purchase</a>
		<a class="btn" href={links.newVisit()}>+ Restaurant visit</a>
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

<div class="top">
	<section class="card map-card">
		<div class="sec-head">
			<h2>Your wine map</h2>
			<a class="more" href={links.map()}>The map →</a>
		</div>
		<HomeMap />
	</section>
	<section class="latest">
		<div class="sec-head">
			<h2>Latest tasting</h2>
			<a class="more" href={links.tastings()}>All tasting notes →</a>
		</div>
		{#if latest}
			<OccasionCard occasion={latest} regionColors={data.regionColors} />
		{:else}
			<p class="card muted pad">No tastings yet. <a class="more" href={links.newTasting()}>Add the first one</a></p>
		{/if}
	</section>
</div>

{#if recentTastings.length > 1}
	<TastingRibbon tastings={recentTastings} label="Recent tastings: every wine of the past year, its region’s colour (its own below)" />
{/if}

<div class="drink">
	<section class="card soon">
		<div class="sec-head">
			<h2>Drink soon</h2>
			<a class="more" href={links.cellar({ view: 'list' })}>The cellar →</a>
		</div>
		{#if d.drink_soon.lines.length}
			<ul class="soon-list">
				{#each d.drink_soon.lines as l (l.bottle_id)}
					<li>
						<span class="end"><BottleEnd region={regionColor(l.region)} color={l.color} format={l.format} size={11} title="{regionLabel(l.region)} · {l.color ?? ''}" /></span>
						<div class="p-main">
							<a href={links.bottle(l.bottle_id)}>{wineName(l)}</a> <span class="muted num">{l.vintage}</span>
							<CriticPills scores={l.scores} />
							<div class="muted small">
								<span class="loc">{l.location}</span> · drink {windowLabel(l.drink_from, l.drink_to)}
								<span class="mosaic" title={plural(l.qty, 'bottle')}>
									{#each times(l.qty) as i (i)}<BottleEnd region={regionColor(l.region)} color={l.color} format={l.format} size={8} />{/each}
								</span>
							</div>
						</div>
						<span class="when"><MaturityBadge maturity={l.maturity} from={l.drink_from} to={l.drink_to} left={l.years_left} /></span>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="muted small">No drinking windows yet: set one on a wine (Edit wine).</p>
		{/if}
		<p class="muted small totals">
			{d.drink_soon.bottles.ready} bottles ready · {d.drink_soon.bottles.young} too young · {d.drink_soon.bottles.past} past
			{#if d.drink_soon.bottles.unknown} · {d.drink_soon.bottles.unknown} without a window{/if}
		</p>
	</section>
	<WhatToOpen bottles={data.cellar.bottles} />
</div>

{#if d.nudges.length}
	<section class="card nudges">
		<h2>Waiting in the cellar</h2>
		<p class="muted">Regions you hold bottles from but haven't opened anything from in over a year.</p>
		<div class="chips">
			{#each d.nudges as n (n.region)}
				<a class="nudge" href={links.region(n.region)} style:--c={n.color ?? FALLBACK_REGION}>
					<b>{regionLabel(n.region)}</b>
					<span class="mosaic" title={plural(n.bottles, 'bottle')}>
						{#each times(n.bottles) as i (i)}<BottleEnd region={n.color ?? FALLBACK_REGION} color={null} size={9} />{/each}
						{#if n.bottles > MOSAIC}<span class="muted more-n num">+{n.bottles - MOSAIC}</span>{/if}
					</span>
					<span class="muted">{plural(n.bottles, 'bottle')} · {since(n.last_tasted)}</span>
				</a>
			{/each}
		</div>
	</section>
{/if}

<section class="card purchases-card">
	<div class="sec-head">
		<h2>Recent purchases <span class="muted num">{plural(recentQty, 'bottle')}</span></h2>
		<a class="more" href={links.cellar()}>The cellar →</a>
	</div>
	{#if recentBottles.length}
		<CellarCards bottles={recentBottles} regionColors={data.regionColors} />
	{:else}
		<p class="muted">No purchases yet. <a class="more" href={links.newBottle()}>Add one</a></p>
	{/if}
</section>

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
	.nudges p {
		margin: 4px 0 10px;
		font-size: 12px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.nudge {
		display: flex;
		flex-direction: column;
		gap: 1px;
		padding: 8px 12px;
		border-radius: 10px;
		border: 1px solid var(--border);
		border-left: 4px solid var(--c);
		color: inherit;
		text-decoration: none;
		font-size: 13px;
		min-width: 150px;
	}
	.nudge:hover {
		border-color: var(--accent);
		border-left-color: var(--c);
	}
	.nudge .muted {
		font-size: 11px;
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
	.when {
		margin-left: auto;
		font-size: 12px;
	}
	ul {
		list-style: none;
		margin: 4px 0 0;
		padding: 0;
		font-size: 13px;
	}
	.end {
		display: flex;
		flex: none;
		align-self: center;
	}
	.p-main {
		flex: 1;
		min-width: 0;
	}
	.loc {
		margin-left: 6px;
		padding: 1px 6px;
		border-radius: 4px;
		background: var(--surface-2);
		font-size: 12px;
	}
	.small {
		font-size: 12px;
	}
	.top {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		gap: 14px;
		margin-bottom: 14px;
		align-items: start;
	}
	@media (max-width: 900px) {
		.top {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	.map-card {
		margin-bottom: 0;
		padding: 14px 14px 12px;
	}
	.latest .sec-head {
		padding: 14px 4px 0;
	}
	.latest :global(.occ) {
		margin: 0;
	}
	.pad {
		padding: 16px 18px;
	}
	.mosaic {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 2px;
		vertical-align: middle;
		margin-left: 4px;
	}
	.nudge .mosaic {
		margin: 3px 0 2px;
		max-width: 220px;
	}
	.more-n {
		font-size: 11px;
		margin-left: 3px;
	}
	.purchases-card h2 .muted {
		font-weight: 400;
		font-size: 13px;
		margin-left: 6px;
	}
	.drink {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
		gap: 14px;
		margin-bottom: 14px;
	}
	.soon {
		padding: 16px 18px;
	}
	.soon-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.soon-list li {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 0;
		border-top: 1px solid var(--border);
		font-size: 13px;
	}
	.when {
		flex: none;
	}
	.totals {
		margin: 8px 0 0;
	}
</style>
