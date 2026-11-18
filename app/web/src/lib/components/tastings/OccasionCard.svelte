<script lang="ts">
	import { labelTip } from '#lib/labelTip.svelte.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import CriticPills from '#lib/components/CriticPills.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { placeMeta } from '#lib/places.ts';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { photoSrc } from '#lib/api/photos.ts';
	import { opensImage } from '#lib/lightbox.svelte.ts';
	import { fmtDay, stars } from './journal.ts';
	import { plainText } from '#lib/notes.ts';
	import type { Occasion } from './journal.ts';

	/** plain: a row in a list (the home page's latest tastings), not a card: its day and place small on a line,
	 * then its wines */
	/** onwine: a wine pointed at (hovered, or tapped outside its links), e.g. for a map to show it; `shown` marks the
	 * wine shown there */
	let {
		occasion: o,
		regionColors,
		plain = false,
		onwine,
		shown = null,
		onplace
	}: {
		occasion: Occasion;
		regionColors: RegionColors;
		plain?: boolean;
		onwine?: (w: Occasion['wines'][number]) => void;
		shown?: number | null;
		/** its place pointed at (its header hovered, or tapped outside its links): for a map to pin it; only for a
		 * place with its coordinates */
		onplace?: (where: [number, number]) => void;
	} = $props();
	const where = $derived<[number, number] | null>(o.place?.lat != null && o.place?.lng != null ? [o.place.lng, o.place.lat] : null);

	const meta = $derived(o.place ? placeMeta(o.place) : '');
</script>

{#if o.visit}
	<!-- A restaurant visit without wine: one line, everything in the header -->
	<article class="occ visit">
		<header>
			{#if o.photo}
				<a class="thumb" href={photoSrc(o.photo, 'large')} use:opensImage title="Open the photo">
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
				{#if o.visit.notes}<span class="visit-notes" title={plainText(o.visit.notes)}>{plainText(o.visit.notes)}</span>{/if}
			</div>
			<a class="action" href={links.editVisit(o.visit.id)}>Edit</a>
			<span class="date num">{fmtDay(o.date)}</span>
		</header>
	</article>
{:else}
<!-- An occasion: when and where at the side, then its wines, each with its note beside it (under it on a phone, and
     in a list: plain) -->
<article class="occ" class:plain>
	<!-- The evening's palette: one segment per wine, in its region's color, in the order they were poured -->
	<div class="palette" aria-hidden="true">
		{#each o.wines as w (w.id)}<span style:background={regionColors[w.region] ?? FALLBACK_REGION}></span>{/each}
	</div>
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions, a11y_no_static_element_interactions -->
	<header
		class:points={!!(onplace && where)}
		onpointerenter={(e) => e.pointerType === 'mouse' && appSettings.map_follow === 'hover' && where && onplace?.(where)}
		onclick={(e) => !(e.target as HTMLElement).closest('a, button') && where && onplace?.(where)}
	>
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
		{#if o.photo && !plain}
			<a class="photo" href={photoSrc(o.photo, 'large')} use:opensImage title="Open the photo">
				<img src={photoSrc(o.photo, 'thumb')} alt="{o.name}, {o.date}" loading="lazy" decoding="async" />
			</a>
		{/if}
	</header>
	<div class="body">
		{#if o.photo && plain}<img src={photoSrc(o.photo, 'thumb')} alt="{o.name}, {o.date}" loading="lazy" decoding="async" />{/if}
		<div class="content">
			<!-- the evening's own note (the menu...): it opens the evening -->
			{#if o.evening?.notes && o.wines[0]}
				<a class="evening" href={links.tasting(o.wines[0].id)} title="Open the evening">{plainText(o.evening.notes)}</a>
			{/if}
			<ul>
				{#each o.wines as w (w.id)}
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
					<li
						class:shown={onwine && shown === w.id}
						class:points={!!onwine}
						onpointerenter={(e) => e.pointerType === 'mouse' && appSettings.map_follow === 'hover' && onwine?.(w)}
						onclick={(e) => !(e.target as HTMLElement).closest('a') && onwine?.(w)}
					>
						<div class="wine">
							<div class="line">
								<span class="end" use:labelTip={w.label}>
									<BottleEnd
										region={regionColors[w.region] ?? FALLBACK_REGION}
										color={w.color}
										format={w.format}
										size={11}
										title="{regionLabel(w.region)} · {w.color ?? ''}{w.format ? ` · ${w.format}` : ''}"
									/>
								</span>
								<span class="label">
									<a href={links.wine(w.wine_id)}><b>{w.producer}</b>{w.cuvee ? ` – ${w.cuvee}` : ''}</a>
									<span class="vintage num">{w.vintage}</span><CriticPills scores={w.scores} />{#if w.rating}<span class="mine num" title="Your score">{w.rating}</span>{/if}
								</span>
								<!-- no note yet: a small pencil at the line's end opens the tasting to write one -->
								{#if !w.notes}<a class="add-note" href={links.tasting(w.id)} title="Add a note" aria-label="Add a note to {w.producer} {w.cuvee}"><Icon name="edit" size={13} /></a>{/if}
							</div>
							{#if w.appellation}<div class="under muted">{w.appellation}</div>{/if}
						</div>
						<!-- the note opens the tasting -->
						{#if w.notes}
							<div class="said">
								<a class="note" href={links.tasting(w.id)} title="Open the tasting">{w.notes}</a>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	</div>
</article>
{/if}

<style>
	/* An occasion: a card, when and where in a column at its side, its wines beside, each with its note at the right */
	.occ {
		display: grid;
		grid-template-columns: 200px minmax(0, 1fr);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		background: var(--surface);
	}
	.palette {
		grid-column: 1 / -1;
		display: flex;
		gap: 1px;
		height: 3px;
	}
	.palette span {
		flex: 1;
	}
	header {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		min-width: 0;
		padding: 14px 0 14px 16px;
	}
	.where {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 2px 8px;
		min-width: 0;
		max-width: 100%;
	}
	.name {
		font-family: var(--heading-font);
		font-weight: 650;
		font-size: 15px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	a.name {
		color: var(--text);
		text-decoration: var(--link-decoration, none);
	}
	a.name:hover {
		color: var(--accent);
	}
	.stars {
		color: var(--gold-text);
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
		order: -1;
		font-size: 12px;
		white-space: nowrap;
	}
	.meta {
		font-size: 12px;
	}
	.meta:empty {
		display: none;
	}
	.action {
		margin-top: 4px;
		color: var(--muted);
		font-size: 12px;
		white-space: nowrap;
	}
	.action:hover {
		color: var(--accent);
	}
	.photo {
		display: block;
		margin-top: 8px;
		line-height: 0;
	}
	.photo img {
		width: 100%;
		max-height: 170px;
		object-fit: cover;
		border-radius: 6px;
	}
	.body {
		min-width: 0;
		padding: 8px 16px 10px 20px;
	}
	.content {
		min-width: 0;
	}
	.evening {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		overflow: hidden;
		margin: 0 0 8px;
		font-size: 13px;
		color: var(--muted);
		white-space: pre-line;
		text-decoration: none;
	}
	.evening:hover {
		color: var(--text);
	}
	ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	li {
		display: grid;
		grid-template-columns: minmax(0, 5fr) minmax(0, 6fr);
		gap: 4px 24px;
		padding: 7px 0;
		font-size: 13px;
	}
	li + li {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.wine,
	.said {
		min-width: 0;
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
		margin-left: 19px;
		font-size: 12px;
	}
	.add-note {
		flex: none;
		align-self: center;
		display: inline-flex;
		padding: 2px;
		color: var(--muted);
		opacity: 0.7;
	}
	.add-note:hover {
		color: var(--accent);
		opacity: 1;
	}
	/* the note opens the tasting: a few lines here, the whole on its page */
	.note {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 6;
		line-clamp: 6;
		overflow: hidden;
		color: var(--text);
		font-style: italic;
		white-space: pre-line;
		text-decoration: none;
	}
	.note:hover {
		color: var(--accent);
	}
	/* A phone: when and where on top, each note under its wine */
	@media (max-width: 760px) {
		.occ {
			display: block;
		}
		header {
			padding: 12px 16px 0;
		}
		.photo img {
			max-height: 220px;
		}
		.body {
			padding: 6px 16px 10px;
		}
		li {
			display: block;
		}
		.said {
			margin: 3px 0 0 19px;
		}
	}
	/* In the column over a full-size map (the Tasting Notes page's): laid out as on a phone, when and where on top,
	   each note under its wine */
	:global(html.map-full) .occ:not(.plain) {
		display: block;
	}
	:global(html.map-full) .occ:not(.plain) header {
		padding: 12px 16px 0;
	}
	:global(html.map-full) .occ:not(.plain) .photo img {
		max-height: 220px;
	}
	:global(html.map-full) .occ:not(.plain) .body {
		padding: 6px 16px 10px;
	}
	:global(html.map-full) .occ:not(.plain) li {
		display: block;
	}
	:global(html.map-full) .occ:not(.plain) .said {
		margin: 3px 0 0 19px;
	}
	/* A row in a list (the home page's latest tastings): no card, the day and the place small on a line, each note
	   under its wine */
	.occ.plain {
		display: block;
		border: 0;
		border-radius: 0;
		background: none;
		overflow: visible;
	}
	.plain .palette {
		display: none;
	}
	.plain header {
		flex-direction: row;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 2px 8px;
		padding: 0;
		font-size: 12px;
	}
	.plain .where {
		flex: 0 1 auto;
	}
	.plain .name {
		font-family: inherit;
		font-size: 12px;
		font-weight: 400;
		color: var(--muted);
	}
	.plain .action {
		margin: 0 0 0 auto;
	}
	.plain .body {
		display: flex;
		flex-wrap: wrap-reverse;
		gap: 14px;
		padding: 6px 0 0;
	}
	.plain .content {
		flex: 1 1 300px;
	}
	.plain .body > img {
		flex: 0 1 180px;
		max-width: 100%;
		max-height: 240px;
		object-fit: cover;
		border-radius: 6px;
	}
	.plain li {
		display: block;
		padding: 5px 0;
	}
	.plain .said {
		margin: 3px 0 0 19px;
	}
	.plain .note {
		-webkit-line-clamp: 3;
		line-clamp: 3;
	}
	/* Restaurant visits: a tinted one-line card, so they read apart from tastings */
	.visit {
		border-color: color-mix(in srgb, var(--gold) 45%, var(--border));
	}
	.occ.visit {
		display: block;
	}
	.visit header {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		background: color-mix(in srgb, var(--gold) 14%, var(--surface));
		padding: 7px 14px;
	}
	.visit .date {
		order: 0;
		color: var(--muted);
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
	/* a wine that shows itself on a map when pointed at; the one shown on a soft tint (no outline: its pip at the
	   left is the line's mark), with room around the pip */
	li.points {
		margin-inline: -8px;
		padding-inline: 8px;
		border-radius: 6px;
		cursor: pointer;
		transition: background 0.15s;
	}
	li.points:hover {
		background: color-mix(in srgb, var(--accent) 5%, transparent);
	}
	li.shown,
	li.shown:hover {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}
	/* a header whose place shows on a map when pointed at */
	header.points {
		cursor: pointer;
	}
	header.points:hover .name {
		color: var(--accent);
	}
</style>
