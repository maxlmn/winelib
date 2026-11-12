<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import type { Tasting, TastingPlace, Visit } from '#lib/api/details.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import { links } from '#lib/links.ts';
	import { photoSrc } from '#lib/api/photos.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import LabelThumbs from './LabelThumbs.svelte';
	import { fmtDate, stars } from './wine.ts';

	interface Props {
		tastings: Tasting[];
		regionColors: RegionColors;
		/** on a place's own page: one card per day, logged visits merged in */
		place?: TastingPlace | null;
		visits?: Visit[];
		empty?: string;
		/** the wines' labels (a producer's page): each wine's, small, opening larger */
		labels?: Record<number, { url: string; from_vintage: string | null }>;
	}

	let { tastings, regionColors, place = null, visits = [], empty = 'No tastings recorded yet.', labels = {} }: Props = $props();

	const PAGE = 40;
	let limit = $state(PAGE);

	interface Day {
		key: string;
		date: string | null;
		place: TastingPlace | null;
		/** free-text location when there is no place */
		location: string | null;
		visit: Visit | null;
		wines: Tasting[];
	}

	// One card per day and place
	const days = $derived.by(() => {
		const byKey = new Map<string, Day>();
		const day = (key: string, init: () => Day) => byKey.get(key) ?? byKey.set(key, init()).get(key)!;
		for (const t of tastings) {
			const where = place ? '' : t.place ? `p${t.place.id}` : `l${t.location ?? ''}`;
			day(`${t.date}|${where}`, () => ({
				key: `${t.date}|${where}`, date: t.date, place: place ?? t.place, location: t.location, visit: null, wines: []
			})).wines.push(t);
		}
		for (const v of visits) {
			const d = byKey.get(`${v.date}|`);
			if (d && !d.visit) d.visit = v;
			else byKey.set(`visit${v.id}`, { key: `visit${v.id}`, date: v.date, place, location: null, visit: v, wines: [] });
		}
		return [...byKey.values()].sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''));
	});

	const regionColor = (r: string | null) => (r && regionColors[r]) || FALLBACK_REGION;
</script>

{#if !days.length}
	<p class="muted">{empty}</p>
{:else}
	<!-- Plain rows, a day at a time: when and where at the side (small), the wines and their notes -->
	<ul class="days">
		{#each days.slice(0, limit) as d (d.key)}
			{@const photo = d.wines.find((w) => w.photo)?.photo ?? d.visit?.photo}
			<li class="day">
				<div class="when">
					{#if d.date && d.wines.length}
						<!-- the occasion in the journal: every wine of that day there -->
						<a class="date num" href={links.occasion(d.date, d.place?.name ?? d.location)} title="Open the occasion in the journal">{fmtDate(d.date)}</a>
					{:else}
						<span class="date num">{fmtDate(d.date)}</span>
					{/if}
					{#if d.place && !place}
						<a class="venue" href={links.place(d.place.id)}><PlaceName name={d.place.name} type={d.place.type} />{#if d.place.michelin_stars}<span class="stars">{stars(d.place.michelin_stars)}</span>{/if}</a>
					{:else if !place && d.location}
						<span class="venue">{d.location}</span>
					{/if}
				</div>
				<div class="what">
					{#if d.visit}
						<div class="visit">
							<span class="badge">Visit</span>
							{#if d.visit.notes}<span class="visit-notes">{d.visit.notes}</span>{:else}<span class="muted">No notes.</span>{/if}
							<a class="edit" href={links.editVisit(d.visit.id)}>Edit</a>
						</div>
					{/if}
					{#each d.wines as t (t.id)}
						<div class="wine">
							<span class="end">
								<BottleEnd
									region={regionColor(t.region)}
									color={t.color}
									format={t.format}
									size={11}
									title="{regionLabel(t.region)} · {t.color ?? ''}{t.format ? ` · ${t.format}` : ''}"
								/>
							</span>
							<div class="line">
								<a href={links.wine(t.wine_id)}><b>{t.producer}</b>{t.cuvee ? ` – ${t.cuvee}` : ''}</a>
								<span class="vintage num">{t.vintage}</span><CriticPills scores={t.scores} />{#if t.rating}<span class="mine num" title="Your score">{t.rating}</span>{/if}
								<!-- under the wine: its appellation, and the note (or the offer to write one), which opens the tasting -->
								<div class="under">
									{#if t.appellation}<span class="muted">{t.appellation}</span>{/if}
									{#if !t.notes}<a class="add-note" href={links.tasting(t.id)} title="Open the tasting">Add a note</a>{/if}
								</div>
								{#if t.notes}<a class="note" href={links.tasting(t.id)} title="Open the tasting">{t.notes}</a>{/if}
							</div>
							{#if labels[t.wine_id] && appSettings.wine_labels !== 'off'}
								{@const l = labels[t.wine_id]}
								<span class="thumb"><LabelThumbs labels={[{ url: l.url, vintages: [l.from_vintage ?? t.vintage] }]} name={t.cuvee || t.producer} /></span>
							{/if}
						</div>
					{/each}
				</div>
				{#if photo}
					<!-- the day's photo, large enough to see; a click opens it whole -->
					<a class="photo" href={photoSrc(photo, 'large')} target="_blank" rel="noopener" title="Open the photo">
						<img src={photoSrc(photo, 'thumb')} alt="{d.place?.name ?? d.location ?? 'Occasion'}, {fmtDate(d.date)}" loading="lazy" decoding="async" />
					</a>
				{/if}
			</li>
		{/each}
	</ul>
	{#if days.length > limit}
		<button class="btn more" onclick={() => (limit += PAGE)}>Show more ({days.length - limit} days)</button>
	{/if}
{/if}

<style>
	.days {
		list-style: none;
		margin: -8px 0;
		padding: 0;
	}
	.day {
		display: grid;
		grid-template-columns: 130px minmax(0, 1fr) auto;
		gap: 4px 16px;
		padding: 10px 0;
		font-size: 13px;
	}
	.day + .day {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.when {
		display: flex;
		flex-direction: column;
		gap: 1px;
		min-width: 0;
		font-size: 12px;
		color: var(--muted);
	}
	.date {
		color: var(--text);
		white-space: nowrap;
	}
	.venue {
		color: var(--muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	a.date:hover,
	a.venue:hover {
		color: var(--accent);
	}
	.stars {
		color: var(--gold-text);
		margin-left: 4px;
	}
	.what {
		min-width: 0;
	}
	.visit {
		display: flex;
		align-items: baseline;
		gap: 8px;
		margin-bottom: 6px;
	}
	.visit-notes {
		font-style: italic;
	}
	.badge {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 1px 6px;
		border-radius: 6px;
		background: var(--accent-soft);
		color: var(--accent);
		flex: none;
	}
	.edit {
		margin-left: auto;
		font-size: 12px;
		color: var(--accent);
	}
	.wine {
		display: flex;
		gap: 8px;
	}
	.wine + .wine {
		margin-top: 8px;
	}
	.end {
		display: flex;
		flex: none;
		margin-top: 3px;
	}
	.thumb {
		flex: none;
	}
	.line {
		flex: 1;
		min-width: 0;
	}
	.vintage {
		color: var(--muted);
		margin-left: 2px;
	}
	.under {
		display: flex;
		justify-content: space-between;
		gap: 10px;
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
		margin: 3px 0 0;
		color: var(--text);
		font-style: italic;
		white-space: pre-line;
		text-decoration: none;
	}
	.note:hover {
		color: var(--accent);
	}
	.photo {
		display: block;
		align-self: start;
		line-height: 0;
	}
	.photo img {
		width: 220px;
		max-width: 100%;
		max-height: 240px;
		object-fit: cover;
		border-radius: 6px;
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
	.more {
		margin-top: 12px;
	}
	/* A phone: when and where on one line above the wines */
	@media (max-width: 760px) {
		.day {
			grid-template-columns: minmax(0, 1fr) auto;
		}
		.when {
			grid-column: 1 / -1;
			flex-direction: row;
			gap: 8px;
		}
		/* the photo under the day's wines, the row's width */
		.what,
		.photo {
			grid-column: 1 / -1;
		}
		.photo img {
			width: 100%;
			max-height: 320px;
		}
	}
</style>
