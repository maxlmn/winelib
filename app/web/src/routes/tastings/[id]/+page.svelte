<script lang="ts">
	import ActionMenu from '#lib/components/ActionMenu.svelte';
	import CriticPills from '#lib/components/CriticPills.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { plural, money } from '#lib/format.ts';
	import { photoSrc } from '#lib/api/photos.ts';
	import { fmtDay, stars, wineName } from '#lib/components/tastings/journal.ts';
	import ShareSticker from '#lib/components/tastings/ShareSticker.svelte';

	let { data } = $props();

	const t = $derived(data.tasting);
	const w = $derived(t.wine);
	const b = $derived(t.bottle);
	const position = $derived(t.occasion.findIndex((o) => o.id === t.id));
	const drinkWindow = $derived(w.drink_from || w.drink_to ? `${w.drink_from ?? '…'}–${w.drink_to ?? '…'}` : null);
	const price = $derived(
		b.price_base ? `${money(b.price_base)}${b.currency && b.currency !== appSettings.currency ? ` (${b.price} ${b.currency})` : ''}` : null
	);
	// The header's two lines: this bottle (its size, vendor, price, date: a link to it) and the wine (what its page's
	// header line says: grapes, blend, disgorgement, drinking window, vineyard)
	const bottleLine = $derived([b.format, b.vendor, price, b.purchase_date && `bought ${b.purchase_date}`].filter(Boolean).join(' · '));
	const grapes = $derived(w.grapes?.length ? w.grapes : w.varietal ? [{ id: 0, name: w.varietal, share: null }] : []);
	const others = $derived(t.occasion.length > 1);
	// The critics with a score ("-": searched, none found)
	const critics = $derived(w.scores.filter((s) => s.score && !['-', '0'].includes(s.score.trim())));
	// For the share sticker: this wine and your note, the evening's wines in order (no score: the journal's 90 is a
	// default, not one)
	const sticker = $derived({
		wine: { producer: w.producer, cuvee: w.cuvee, vintage: w.vintage, color: w.color, region: w.region, appellation: w.appellation?.name ?? null, notes: t.notes },
		session: t.occasion.map((o) => ({ producer: o.producer, cuvee: o.cuvee, vintage: o.vintage, color: o.color, region: o.region ?? null, appellation: o.appellation ?? null, notes: o.notes ?? '' })),
		when: t.date ? fmtDay(t.date) : '',
		// a friend's home is named after them: "At Claude's"
		where: [t.place?.type === "Friend's Place" ? `At ${t.place.name}’s` : (t.place?.name ?? t.location), t.place?.city].filter(Boolean).join(', '),
		filename: `${[w.producer, w.cuvee, w.vintage].filter(Boolean).join('-')}`.toLowerCase().replace(/[^a-z0-9]+/g, '-')
	});
</script>

<svelte:head><title>{wineName(w)} · {t.date} · WineLib</title></svelte:head>

<a class="back muted" href={links.tastings()}>← Tasting notes</a>

<div class="head">
	<div>
		<div class="kind"><Icon name="glass" size={12} />Tasting</div>
		<div class="kicker">
			{#if w.region}<span class="swatch" style:background={w.region_color ?? FALLBACK_REGION}></span><a class="kicker-link" href={links.region(w.region)}>{regionLabel(w.region)}</a>{/if}
			{#if w.appellation}{#if w.region} · {/if}<a class="kicker-link" href={links.appellation(w.appellation.id)}>{w.appellation.name}</a>{/if}
		</div>
		<h1>
			<span class="bottle"><BottleEnd region={w.region_color ?? FALLBACK_REGION} color={w.color} format={b.format} size={20} title="{regionLabel(w.region)} · {w.color ?? ''}" /></span>
			<a href={links.wine(w.id)}>{w.producer}{w.cuvee ? ` ${w.cuvee}` : ''}</a> <span class="vintage num">{w.vintage}</span></h1>
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
		{#if grapes.length || w.blend || w.disgorged || drinkWindow || w.vineyard}
			<p class="line">
				{#each grapes as g, i (g.name)}{#if i}, {/if}<a href={links.grape(g.name)}>{g.name}</a>{#if g.share && g.share < 100}{' '}<span class="muted num">{+g.share.toFixed(1)}%</span>{/if}{/each}
				{#if w.blend}<span class="item">{w.blend}</span>{/if}
				{#if w.disgorged}<span class="item">Disgorged {w.disgorged}</span>{/if}
				{#if drinkWindow}<span class="item">Drink <span class="num">{drinkWindow}</span></span>{/if}
				{#if w.vineyard}<span class="item"><a href={links.vineyard(w.vineyard.id)}>{w.vineyard.label}</a></span>{/if}
			</p>
		{/if}
		{#if bottleLine}<a class="line bottle-line muted" href={links.bottle(b.id)}>{bottleLine} ›</a>{/if}
	</div>
	<div class="page-actions">
		<ActionMenu>
			<a class="menu-item" role="menuitem" href={links.newTasting({ place_id: t.place?.id, date: t.date })}><Icon name="glass" size={15} />Add a wine to this occasion</a>
			<hr />
			<a class="menu-item" role="menuitem" href={links.editBottle(b.id)}><Icon name="bottle" size={15} />Edit the bottle</a>
		</ActionMenu>
		<a class="btn icon primary" href={links.editTasting(t.id)} title="Edit tasting" aria-label="Edit tasting"><Icon name="edit" size={15} /></a>
		<ShareSticker {...sticker} />
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
			{#each critics as s (s.critic)}
				<div><div class="label">{s.critic}</div><div class="value num">{#if s.url}<a href={s.url} target="_blank" rel="noreferrer" title="The review">{s.score} ↗</a>{:else}{s.score}{/if}</div></div>
			{/each}
		</div>
		{#each critics.filter((c) => c.note) as s (s.critic)}
			<p class="review"><span class="label">{s.critic}</span> {s.note}</p>
		{/each}
		{#if t.styles?.length}
			<div class="tags styles" title="The wine's style, as you found it">{#each t.styles as s (s)}<span class="tag style">{s}</span>{/each}</div>
		{/if}
		{#if t.tags}
			<div class="tags">{#each t.tags.split(',').map((x) => x.trim()).filter(Boolean) as tag}<span class="tag">{tag}</span>{/each}</div>
		{/if}
		{#if t.photo}
			<a class="photo" href={t.photo} target="_blank" rel="noopener" title="Open the full-size photo">
				<img src={photoSrc(t.photo, 'large')} alt="{t.location}, {t.date}" decoding="async" />
			</a>
		{/if}
	</section>

	{#if others}
	<section class="card">
		<h2>That session <span class="muted num">{plural(t.occasion.length, 'wine')}</span></h2>
		<ol class="occasion">
			{#each t.occasion as o (o.id)}
				<li class:current={o.id === t.id}>
					<BottleEnd region={regionColor(o.region) ?? FALLBACK_REGION} color={o.color} size={11} title="{regionLabel(o.region ?? null)} · {o.color ?? ''}" />
					<a href={links.tasting(o.id)}><b>{o.producer}</b>{o.cuvee ? ` ${o.cuvee}` : ''} <span class="muted num">{o.vintage}</span></a>
					{#if o.rating}<span class="mine num" title="Your score">{o.rating}</span>{/if}
					<CriticPills scores={o.scores} />
				</li>
			{/each}
		</ol>
	</section>
	{/if}



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
	/* what this page is, as on the other detail pages */
	.kind {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
		margin-bottom: 2px;
	}
	/* the wine's line and the bottle's, under the date and place */
	.line {
		margin: 4px 0 0;
		font-size: 14px;
	}
	.line a {
		color: inherit;
	}
	.line a:hover,
	a.bottle-line:hover {
		color: var(--accent);
	}
	.line .item::before {
		content: '·';
		margin: 0 8px;
		color: var(--muted);
	}
	.line > .item:first-child::before {
		content: none;
		margin: 0;
	}
	a.bottle-line {
		display: block;
		font-size: 13px;
		text-decoration: none;
	}
	.review {
		margin: 8px 0 0;
		font-size: 13px;
		color: var(--muted);
	}
	.review .label {
		margin-right: 6px;
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
	.tag.style {
		background: none;
		border: 1px solid var(--accent);
		color: var(--accent);
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
	.bottle {
		display: inline-block;
		margin-right: 8px;
		transform: translateY(-2px);
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
