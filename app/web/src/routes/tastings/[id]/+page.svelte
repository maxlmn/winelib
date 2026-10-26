<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import { grapesText } from '#lib/grapes.ts';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { plural, money } from '#lib/format.ts';
	import { photoSrc } from '#lib/api/photos.ts';
	import { fmtDay, stars, wineName } from '#lib/components/tastings/journal.ts';

	let { data } = $props();

	const t = $derived(data.tasting);
	const w = $derived(t.wine);
	const b = $derived(t.bottle);
	const position = $derived(t.occasion.findIndex((o) => o.id === t.id));
	const drinkWindow = $derived(w.drink_from || w.drink_to ? `${w.drink_from ?? '…'}–${w.drink_to ?? '…'}` : null);
	const price = $derived(
		b.price_base ? `${money(b.price_base)}${b.currency && b.currency !== appSettings.currency ? ` (${b.price} ${b.currency})` : ''}` : null
	);
	const fields = (rows: [string, string | number | null | undefined][]) => rows.filter(([, v]) => v !== null && v !== undefined && v !== '');
	// The critics with a score ("-": searched, none found)
	const critics = $derived(w.scores.filter((s) => s.score && !['-', '0'].includes(s.score.trim())));
</script>

<svelte:head><title>{wineName(w)} · {t.date} · WineLib</title></svelte:head>

<a class="back muted" href={links.tastings()}>← Tasting notes</a>

<div class="head">
	<div>
		<div class="kicker">
			<span class="dot" style:background={typeColor(w.color)} title={w.color}></span>
			{#if w.region}<span class="swatch" style:background={w.region_color ?? FALLBACK_REGION}></span><a class="kicker-link" href={links.region(w.region)}>{regionLabel(w.region)}</a>{/if}
			{#if w.appellation} · <a class="kicker-link" href={links.appellation(w.appellation.id)}>{w.appellation.name}</a>{/if}
		</div>
		<h1><a href={links.wine(w.id)}>{w.producer}{w.cuvee ? ` ${w.cuvee}` : ''}</a> <span class="vintage num">{w.vintage}</span></h1>
		<div class="when">
			<span class="num">{t.date ? fmtDay(t.date) : 'Undated'}</span>
			{#if t.place}
				· <a href={links.place(t.place.id)}><PlaceName name={t.place.name} type={t.place.type} /></a>
				{#if t.place.stars}<span class="stars">{stars(t.place.stars)}</span>{/if}
				{#if t.place.city}<span class="muted">· {[t.place.city, t.place.country].filter(Boolean).join(', ')}</span>{/if}
			{:else if t.location}
				· {t.location}
			{/if}
		</div>
	</div>
	<div class="actions">
		<a class="btn primary" href={links.editTasting(t.id)}>✎ Edit tasting</a>
		<a class="btn" href={links.editBottle(b.id)}>Edit bottle</a>
	</div>
</div>

<div class="grid">
	<section class="card note">
		<h2>Tasting note</h2>
		{#if t.notes}
			<blockquote>{t.notes}</blockquote>
		{:else}
			<p class="muted">No notes. <a class="accent" href={links.editTasting(t.id)}>Add one</a></p>
		{/if}
		<div class="metrics">
			{#if t.rating}<div><div class="label">Your score</div><div class="value num mine-value">{t.rating}</div></div>{/if}
			{#if t.glasses}<div><div class="label">Glasses</div><div class="value num">{t.glasses}</div></div>{/if}
			{#if position >= 0 && t.occasion.length > 1}
				<div><div class="label">Order</div><div class="value num">{position + 1}<span class="muted">&nbsp;of {t.occasion.length}</span></div></div>
			{/if}
			{#each critics as s (s.critic)}<div><div class="label">{s.critic}</div><div class="value num">{s.score}</div></div>{/each}
		</div>
		{#if t.tags}
			<div class="tags">{#each t.tags.split(',').map((x) => x.trim()).filter(Boolean) as tag}<span class="tag">{tag}</span>{/each}</div>
		{/if}
		{#if t.photo}
			<a class="photo" href={t.photo} target="_blank" rel="noopener" title="Open the full-size photo">
				<img src={photoSrc(t.photo, 'large')} alt="{t.location}, {t.date}" decoding="async" />
			</a>
		{/if}
	</section>

	<section class="card">
		<h2>That {t.place?.type === 'Home' ? 'day' : 'evening'} <span class="muted num">{plural(t.occasion.length, 'wine')}</span></h2>
		<ol class="occasion">
			{#each t.occasion as o (o.id)}
				<li class:current={o.id === t.id}>
					<span class="dot" style:background={typeColor(o.color)}></span>
					<a href={links.tasting(o.id)}><b>{o.producer}</b>{o.cuvee ? ` ${o.cuvee}` : ''} <span class="muted num">{o.vintage}</span></a>
					{#if o.rating}<span class="mine num" title="Your score">{o.rating}</span>{/if}
					<CriticPills scores={o.scores} />
				</li>
			{/each}
		</ol>
		<a class="accent small" href={links.newTasting({ place_id: t.place?.id, date: t.date })}>+ Add a wine to this occasion</a>
	</section>

	<section class="card">
		<h2>Wine</h2>
		<dl>
			{#each fields([['Producer', w.producer], ['Type', w.color], ['Disgorged', w.disgorged], [w.grapes?.length > 1 ? 'Grapes' : 'Grape', grapesText(w.grapes, w.varietal)], ['Blend', w.blend], ['Drink', drinkWindow]]) as [k, v]}
				<dt>{k}</dt>
				<dd>{#if k === 'Producer'}<a href={links.producer(w.producer_id)}>{v}</a>{:else if k === 'Grape'}<a href={links.grape(String(v))}>{v}</a>{:else if k === 'Grapes'}{#each w.grapes as g, i (g.id)}{#if i}{', '}{/if}<a href={links.grape(g.name)}>{g.name}</a>{#if g.share}&nbsp;{+g.share.toFixed(1)}%{/if}{/each}{:else}{v}{/if}</dd>
			{/each}
			{#if w.appellation}<dt>Appellation</dt><dd><a href={links.appellation(w.appellation.id)}>{w.appellation.name}</a></dd>{/if}
			{#if w.vineyard}<dt>Vineyard</dt><dd><a href={links.vineyard(w.vineyard.id)}>{w.vineyard.label}</a></dd>{/if}
			{#if w.lwin}<dt>LWIN</dt><dd><a href={links.winelabs(w.lwin, w.vintage)} target="_blank" rel="noreferrer">{w.lwin} ↗</a></dd>{/if}
		</dl>
		{#each critics as s (s.critic)}
			<div class="scores">
				<div class="label">{s.critic} {s.score}{#if s.url} · <a href={s.url} target="_blank" rel="noreferrer">Review ↗</a>{/if}</div>
				{#if s.note}<p>{s.note}</p>{/if}
			</div>
		{/each}
		<a class="accent small" href={links.wine(w.id)}>Wine details →</a>
	</section>

	<section class="card">
		<h2>Bottle</h2>
		<dl>
			{#each fields([['Format', b.format], ['Location', b.location], ['Vendor', b.vendor], ['Provenance', b.provenance], ['Price', price], ['Purchased', b.purchase_date]]) as [k, v]}
				<dt>{k}</dt><dd class:num={k === 'Price'}>{v}</dd>
			{/each}
		</dl>
		<a class="accent small" href={links.bottle(b.id)}>Bottle details →</a>
	</section>

	{#if t.history.length}
		<section class="card wide">
			<h2>Other tastings of this wine <span class="muted num">{t.history.length}, all vintages</span></h2>
			<ul class="history">
				{#each t.history as h (h.id)}
					<li>
						<a class="h-date num" href={links.tasting(h.id)}>{h.date}</a>
						<span class="h-vintage num">{h.vintage}</span>
						<span class="h-place muted">{#if h.place_id}<a href={links.place(h.place_id)}>{h.place}</a>{:else}{h.place ?? ''}{/if}</span>
						<span>{#if h.rating}<span class="mine num" title="Your score">{h.rating}</span>{/if}<CriticPills scores={h.scores} /></span>
						<a class="h-note" class:muted={!h.notes} href={links.tasting(h.id)}>{h.notes || 'No notes'}</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>

<style>
	.back {
		font-size: 13px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		flex-wrap: wrap;
		gap: 14px;
		margin: 10px 0 18px;
	}
	.kicker {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--muted);
		margin-bottom: 4px;
	}
	.swatch {
		display: inline-block;
		width: 4px;
		height: 14px;
		border-radius: 2px;
		margin-left: 4px;
	}
	h1 a:hover {
		color: var(--accent);
	}
	.vintage {
		color: var(--muted);
		font-weight: 500;
	}
	.when {
		margin-top: 4px;
	}
	.when a,
	.accent {
		color: var(--accent);
	}
	.stars {
		color: var(--gold);
		letter-spacing: 1px;
		font-size: 12px;
	}
	.actions {
		display: flex;
		gap: 8px;
	}
	.btn.primary:hover {
		color: white;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr));
		gap: 14px;
		align-items: start;
	}
	section {
		padding: 16px 18px;
	}
	.wide {
		grid-column: 1 / -1;
	}
	h2 {
		font-size: 14px;
		margin: 0 0 12px;
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	h2 span {
		font-size: 12px;
		font-weight: 400;
	}
	blockquote {
		margin: 0 0 14px;
		padding: 2px 0 2px 14px;
		border-left: 3px solid var(--accent);
		font-size: 15px;
		line-height: 1.55;
		white-space: pre-line;
	}
	.metrics {
		display: flex;
		flex-wrap: wrap;
		gap: 26px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
	}
	.value {
		font-size: 20px;
		font-weight: 650;
	}
	.value .muted {
		font-size: 13px;
		font-weight: 400;
	}
	.tags {
		display: flex;
		gap: 6px;
		margin-top: 12px;
	}
	.tag {
		font-size: 12px;
		padding: 1px 8px;
		border-radius: 10px;
		background: var(--surface-2);
	}
	.photo {
		display: block;
		width: fit-content;
		cursor: zoom-in;
	}
	img {
		display: block;
		max-width: 100%;
		max-height: 420px;
		margin-top: 14px;
		border-radius: 8px;
	}
	.occasion {
		list-style: none;
		padding: 0;
		margin: 0 0 12px;
		counter-reset: seq;
	}
	.occasion li {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 8px;
		border-radius: 6px;
		font-size: 13px;
		counter-increment: seq;
	}
	.occasion li::before {
		content: counter(seq);
		width: 14px;
		color: var(--muted);
		font-size: 11px;
		font-variant-numeric: tabular-nums;
		text-align: right;
	}
	.occasion li.current {
		background: var(--accent-soft);
	}
	.occasion .dot {
		width: 8px;
		height: 8px;
	}
	.mine {
		padding: 0 6px;
		margin-right: 4px;
		border-radius: 8px;
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		background: var(--accent-soft);
	}
	.mine-value {
		color: var(--accent);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 5px 16px;
		margin: 0 0 12px;
		font-size: 13px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
		min-width: 0;
	}
	dd a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	dd a:hover {
		color: var(--accent);
	}
	.scores {
		padding: 10px 12px;
		margin-bottom: 12px;
		border-radius: 8px;
		background: var(--surface-2);
		font-size: 13px;
	}
	.scores p {
		margin: 4px 0 0;
	}
	.scores a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.scores a:hover {
		color: var(--accent);
	}
	.small {
		font-size: 13px;
	}
	.history {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.history li {
		display: grid;
		grid-template-columns: 90px 90px minmax(100px, 200px) auto 1fr;
		align-items: baseline;
		gap: 12px;
		padding: 6px 0;
		border-bottom: 1px solid var(--border);
		font-size: 13px;
	}
	.history li:last-child {
		border-bottom: none;
	}
	.h-date {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.h-date:hover {
		color: var(--accent);
	}
	.h-vintage {
		font-weight: 600;
	}
	.h-place {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.h-note {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	@media (max-width: 760px) {
		.history li {
			grid-template-columns: auto auto 1fr;
		}
		.h-note {
			grid-column: 1 / -1;
			white-space: normal;
		}
	}
	.kicker-link {
		color: inherit;
	}
	.kicker-link:hover {
		color: var(--accent);
	}
</style>
