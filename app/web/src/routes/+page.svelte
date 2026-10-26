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

	let { data } = $props();
	const d = $derived(data.dashboard);
	const gain = $derived(pct(d.cellar.cost, d.cellar.market));
	const year = $derived(d.today.slice(0, 4));

	const greeting = (() => {
		const h = new Date().getHours();
		return h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
	})();

	// Without a cuvée name: the appellation and grape instead
	const wineName = (w: { producer: string; cuvee: string; appellation: string | null; varietal: string | null }) => {
		const label = w.cuvee || [w.appellation, w.varietal].filter(Boolean).join(' · ');
		return label ? `${w.producer} – ${label}` : w.producer;
	};
	const ago = (iso: string) => {
		const days = Math.round((Date.parse(d.today) - Date.parse(iso)) / 86_400_000);
		return days <= 0 ? 'today' : days === 1 ? 'yesterday' : days < 31 ? `${days} days ago` : fmtDate(iso);
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
							<div class="muted small"><span class="loc">{l.location}</span> · ×{l.qty} · drink {windowLabel(l.drink_from, l.drink_to)}</div>
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
	<WhatToOpen />
</div>

{#if d.nudges.length}
	<section class="card nudges">
		<h2>Waiting in the cellar</h2>
		<p class="muted">Regions you hold bottles from but haven't opened anything from in over a year.</p>
		<div class="chips">
			{#each d.nudges as n (n.region)}
				<a class="nudge" href={links.region(n.region)} style:--c={n.color ?? FALLBACK_REGION}>
					<b>{regionLabel(n.region)}</b>
					<span class="num">{plural(n.bottles, 'bottle')}</span>
					<span class="muted">{since(n.last_tasted)}</span>
				</a>
			{/each}
		</div>
	</section>
{/if}

<div class="cols">
	<section class="card">
		<div class="sec-head">
			<h2>Recent tastings</h2>
			<a class="more" href={links.tastings()}>All tasting notes →</a>
		</div>
		{#each d.occasions as o (`${o.date}|${o.place}`)}
			<div class="occasion">
				<div class="o-head">
					{#if o.place_id}<a class="place" href={links.place(o.place_id)}>{o.place}</a>{:else}<span class="place">{o.place}</span>{/if}
					{#if o.stars}<span class="gold">{'★'.repeat(o.stars)}</span>{/if}
					<span class="muted when">{ago(o.date)}</span>
				</div>
				<ul>
					{#each o.wines as w (w.id)}
						<li>
							<span class="end"><BottleEnd region={regionColor(w.region)} color={w.color} format={w.format} size={11} title="{regionLabel(w.region)} · {w.color ?? ''}" /></span>
							<a href={links.tasting(w.id)}>{wineName(w)}</a>
							<span class="muted num">{w.vintage}</span>
							<CriticPills scores={w.scores} />
						</li>
					{/each}
					{#if o.count > o.wines.length}<li class="muted">and {o.count - o.wines.length} more</li>{/if}
				</ul>
			</div>
		{:else}
			<p class="muted">No tastings yet. <a class="more" href={links.newTasting()}>Add the first one</a></p>
		{/each}
	</section>

	<section class="card">
		<div class="sec-head">
			<h2>Recent purchases</h2>
			<a class="more" href={links.cellar({ view: 'list' })}>The cellar →</a>
		</div>
		<ul class="purchases">
			{#each d.purchases as b (b.bottle_id)}
				<li>
					<span class="end"><BottleEnd region={regionColor(b.region)} color={b.color} format={b.format} size={11} title="{regionLabel(b.region)} · {b.color ?? ''}" /></span>
					<div class="p-main">
						<a href={links.bottle(b.bottle_id)}>{wineName(b)}</a> <span class="muted num">{b.vintage}</span>
						<CriticPills scores={b.scores} />
						<div class="muted small">
							{#if b.region}<a class="quiet" href={links.region(b.region)}>{regionLabel(b.region)}</a>&nbsp;·&nbsp;{/if}{b.date ? fmtDate(b.date) : 'Undated'}
						</div>
					</div>
					<div class="p-side num">
						{#if b.qty}<span>×{b.qty}</span>{#if b.location}<span class="loc">{b.location}</span>{/if}{:else}<span class="muted">drunk</span>{/if}
						{#if b.price}<div class="muted small">{Math.round(b.price)} {b.currency ?? ''}</div>{/if}
					</div>
				</li>
			{:else}
				<li class="muted">No purchases yet.</li>
			{/each}
		</ul>
	</section>
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
	.cols {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
		gap: 14px;
	}
	.cols section.card {
		margin-bottom: 0;
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
	.occasion {
		padding: 8px 0;
		border-bottom: 1px solid var(--border);
	}
	.occasion:last-child {
		border-bottom: none;
	}
	.o-head {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 13px;
	}
	.place {
		font-weight: 600;
		color: inherit;
	}
	.gold {
		color: var(--gold);
		font-size: 11px;
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
	.occasion li {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 2px 0;
	}
	.end {
		display: flex;
		flex: none;
		align-self: center;
	}
	.purchases li {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 7px 0;
		border-bottom: 1px solid var(--border);
	}
	.purchases li:last-child {
		border-bottom: none;
	}
	.p-main {
		flex: 1;
		min-width: 0;
	}
	.p-side {
		text-align: right;
		white-space: nowrap;
		font-size: 13px;
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
	.quiet {
		color: inherit;
	}
	.quiet:hover {
		color: var(--accent);
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
