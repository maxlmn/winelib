<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { placeMeta } from '#lib/places.ts';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { photoSrc } from '#lib/api/photos.ts';
	import { fmtDay, stars } from './journal.ts';
	import type { Occasion } from './journal.ts';

	let { occasion: o, regionColors }: { occasion: Occasion; regionColors: RegionColors } = $props();

	const meta = $derived(o.place ? placeMeta(o.place) : '');
</script>

{#if o.visit}
	<!-- A restaurant visit without wine: one line, everything in the header -->
	<article class="occ visit">
		<header>
			{#if o.photo}
				<a class="thumb" href={photoSrc(o.photo, 'large')} target="_blank" rel="noopener" title="Open the photo">
					<img src={photoSrc(o.photo, 'thumb')} alt="{o.name}, {o.date}" loading="lazy" decoding="async" />
				</a>
			{/if}
			<div class="where">
				{#if o.place}
					<a class="name" href={links.place(o.place.id)}><PlaceName name={o.name} type={o.place.type} /></a>
				{:else}
					<span class="name">{o.name}</span>
				{/if}
				{#if o.place?.stars}<span class="stars" title="{o.place.stars} Michelin star{o.place.stars > 1 ? 's' : ''}">{stars(o.place.stars)}</span>{/if}
				<span class="tag">Visit</span>
				{#if meta}<span class="muted meta-inline">{meta}</span>{/if}
				{#if o.visit.notes}<span class="visit-notes" title={o.visit.notes}>{o.visit.notes}</span>{/if}
			</div>
			<a class="action" href={links.editVisit(o.visit.id)}>Edit</a>
			<span class="date num">{fmtDay(o.date)}</span>
		</header>
	</article>
{:else}
<article class="occ">
	<!-- The evening's palette: one segment per wine, in its region's color, in the order they were poured -->
	<div class="palette" aria-hidden="true">
		{#each o.wines as w (w.id)}<span style:background={regionColors[w.region] ?? FALLBACK_REGION}></span>{/each}
	</div>
	<header>
		<div class="where">
			{#if o.place}
				<a class="name" href={links.place(o.place.id)}><PlaceName name={o.name} type={o.place.type} /></a>
			{:else}
				<span class="name">{o.name}</span>
			{/if}
			{#if o.place?.stars}<span class="stars" title="{o.place.stars} Michelin star{o.place.stars > 1 ? 's' : ''}">{stars(o.place.stars)}</span>{/if}
		</div>
		<span class="date num">{fmtDay(o.date)}</span>
		<span class="muted meta">{meta}</span>
		<a class="action" href={links.newTasting({ place_id: o.place?.id, date: o.date })} title="Add a wine to this occasion">+ Wine</a>
	</header>
	<div class="body">
		{#if o.photo}<img src={photoSrc(o.photo, 'thumb')} alt="{o.name}, {o.date}" loading="lazy" decoding="async" />{/if}
		<div class="content">
				<ul>
					{#each o.wines as w (w.id)}
						<li>
							<div class="line">
								<span class="end">
									<BottleEnd
										region={regionColors[w.region] ?? FALLBACK_REGION}
										color={w.color}
										format={w.format}
										size={11}
										title="{regionLabel(w.region)} · {w.color ?? ''}{w.format ? ` · ${w.format}` : ''}"
									/>
								</span>
								<span class="label">
									<a href={links.wine(w.wine_id)}>
										<b>{w.producer}</b>{w.cuvee ? ` – ${w.cuvee}` : ''}
									</a>
									<span class="vintage num">{w.vintage}</span><CriticPills scores={w.scores} />{#if w.rating}<span class="mine num" title="Your score">{w.rating}</span>{/if}
								</span>
							</div>
							<!-- under the wine: its appellation, and the note (or the offer to write one), which opens the tasting -->
							<div class="under">
								{#if w.appellation}<span class="muted">{w.appellation}</span>{/if}
								{#if !w.notes}<a class="add-note" href={links.tasting(w.id)} title="Open the tasting">Add a note</a>{/if}
							</div>
							{#if w.notes}<a class="note" href={links.tasting(w.id)} title="Open the tasting">{w.notes}</a>{/if}
						</li>
					{/each}
				</ul>
		</div>
	</div>
</article>
{/if}

<style>
	/* An occasion: a plain card, its place and day on top, then its wines; no band, nothing boxed inside */
	.occ {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		background: var(--surface);
	}
	.palette {
		display: flex;
		gap: 1px;
		height: 3px;
	}
	.palette span {
		flex: 1;
	}
	header {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: baseline;
		gap: 1px 10px;
		padding: 12px 16px 0;
	}
	.where {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.name {
		font-family: var(--heading-font);
		font-weight: 650;
		font-size: 16px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	a.name {
		color: var(--text);
		text-decoration: var(--link-decoration, none);
	}
	a.name:hover {
		color: var(--accent);
	}
	.stars {
		color: var(--gold);
		letter-spacing: 1px;
		font-size: 12px;
	}
	.tag {
		font-size: 11px;
		padding: 0 7px;
		border-radius: 10px;
		background: var(--accent-soft);
		color: var(--accent);
	}
	.date {
		color: var(--muted);
		font-size: 12px;
		white-space: nowrap;
	}
	.meta {
		font-size: 12px;
		min-height: 1em;
	}
	.body {
		display: flex;
		flex-wrap: wrap-reverse;
		gap: 14px;
		padding: 10px 16px 14px;
	}
	.content {
		flex: 1 1 300px;
		min-width: 0;
	}
	img {
		flex: 0 1 180px;
		max-width: 100%;
		max-height: 240px;
		object-fit: cover;
		border-radius: 6px;
	}
	.action {
		color: var(--muted);
		font-size: 12px;
		white-space: nowrap;
		justify-self: end;
	}
	.action:hover {
		color: var(--accent);
	}
	ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	li {
		padding: 5px 0;
		font-size: 13px;
	}
	li + li {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.line {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.end {
		display: flex;
		flex: none;
		align-self: center;
	}
	.label {
		flex: 1;
		min-width: 0;
	}
	.vintage {
		color: var(--muted);
		margin-left: 2px;
	}
	/* under the wine's name, in line with it (past the bottle end) */
	.under {
		display: flex;
		justify-content: space-between;
		gap: 10px;
		margin-left: 19px;
		font-size: 12px;
	}
	.add-note {
		margin-left: auto;
		color: var(--muted);
		white-space: nowrap;
	}
	.add-note:hover {
		color: var(--accent);
	}
	/* the note opens the tasting: three lines at most here, the whole on its page */
	.note {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		overflow: hidden;
		margin: 3px 0 2px 19px;
		color: var(--text);
		font-style: italic;
		white-space: pre-line;
		text-decoration: none;
	}
	.note:hover {
		color: var(--accent);
	}
	/* Restaurant visits: a tinted one-line card, so they read apart from tastings */
	.visit {
		border-color: color-mix(in srgb, var(--gold) 45%, var(--border));
	}
	.visit header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		background: color-mix(in srgb, var(--gold) 14%, var(--surface));
		padding: 7px 14px;
	}
	.visit .where {
		flex: 1;
		flex-wrap: nowrap;
	}
	.visit .name {
		flex: none;
		max-width: 45%;
	}
	.visit .tag {
		flex: none;
		background: color-mix(in srgb, var(--gold) 25%, transparent);
		color: var(--text);
	}
	.meta-inline {
		flex: none;
		font-size: 12px;
	}
	.visit-notes {
		min-width: 0;
		font-size: 12px;
		font-style: italic;
		color: var(--muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.thumb {
		flex: none;
		display: block;
		line-height: 0;
	}
	.thumb img {
		width: 34px;
		height: 34px;
		max-height: none;
		border-radius: 4px;
	}
	.mine {
		margin-left: 6px;
		padding: 0 6px;
		border-radius: 8px;
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		background: var(--accent-soft);
	}
</style>
