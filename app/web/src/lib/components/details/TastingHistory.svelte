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
	import { plural } from '#lib/format.ts';
	import { fmtDate, stars } from './wine.ts';

	interface Props {
		tastings: Tasting[];
		regionColors: RegionColors;
		/** on a place's own page: one card per day, logged visits merged in */
		place?: TastingPlace | null;
		visits?: Visit[];
		empty?: string;
	}

	let { tastings, regionColors, place = null, visits = [], empty = 'No tastings recorded yet.' }: Props = $props();

	const PAGE = 40;
	let inline = $state(false);
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

	const anyNotes = $derived(tastings.some((t) => t.notes));
	const regionColor = (r: string | null) => (r && regionColors[r]) || FALLBACK_REGION;
</script>

{#if !days.length}
	<p class="muted">{empty}</p>
{:else}
	{#if anyNotes}
		<label class="toggle"><input type="checkbox" bind:checked={inline} /> Show notes inline</label>
	{/if}
	<div class="days">
		{#each days.slice(0, limit) as d (d.key)}
			{@const photo = d.wines.find((w) => w.photo)?.photo ?? d.visit?.photo}
			<article class="day">
				<header>
					{#if d.place && !place}
						<a class="where" href={links.place(d.place.id)}><PlaceName name={d.place.name} type={d.place.type} /></a>
					{:else if place}
						<span class="where">{d.visit && !d.wines.length ? 'Visit' : plural(d.wines.length, 'wine')}</span>
					{:else}
						<span class="where">{d.location || 'Unknown place'}</span>
					{/if}
					<span class="date num">{fmtDate(d.date)}</span>
				</header>
				<div class="content">
					{#if photo}<img class="photo" src={photoSrc(photo, 'thumb')} alt="{d.place?.name ?? d.location ?? 'Occasion'}, {fmtDate(d.date)}" loading="lazy" decoding="async" />{/if}
					{#if d.place && !place && (d.place.city || d.place.michelin_stars)}
						<div class="meta muted">
							{[d.place.city, d.place.country].filter(Boolean).join(', ')}
							{#if d.place.michelin_stars}<span class="stars">{stars(d.place.michelin_stars)}</span>{/if}
						</div>
					{/if}
					{#if d.visit}
						<div class="visit">
							{#if d.wines.length}<span class="badge">Visit</span>{/if}
							{#if d.visit.notes}<span class="visit-notes">{d.visit.notes}</span>{:else}<span class="muted">No notes.</span>{/if}
							<a class="edit" href={links.editVisit(d.visit.id)}>Edit</a>
						</div>
					{/if}
					{#if d.wines.length}
						<ul>
							{#each d.wines as t (t.id)}
								<li>
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
										<a href={links.wine(t.wine_id)} title={!inline && t.notes ? t.notes : undefined}>
											<b>{t.producer}</b>{t.cuvee ? ` – ${t.cuvee}` : ''}
										</a>
										{#if t.appellation}<span class="muted">({t.appellation})</span>{/if}
										<span class="vintage num">[{t.vintage}]</span><CriticPills scores={t.scores} />{#if t.rating}<span class="mine num" title="Your score">{t.rating}</span>{/if}
										<a class="note-link" href={links.tasting(t.id)} title={t.notes ? 'Open the tasting note' : 'No note yet: open the tasting'}>
											{t.notes ? '✎' : '＋'}
										</a>
										{#if inline && t.notes}
											<a class="note" href={links.tasting(t.id)}>{t.notes}</a>
										{/if}
									</div>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			</article>
		{/each}
	</div>
	{#if days.length > limit}
		<button class="btn more" onclick={() => (limit += PAGE)}>Show more ({days.length - limit} days)</button>
	{/if}
{/if}

<style>
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--muted);
		margin-bottom: 12px;
		cursor: pointer;
	}
	.toggle input {
		accent-color: var(--accent);
		margin: 0;
	}
	.days {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 420px), 1fr));
		gap: 12px;
		align-items: start;
	}
	.day {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 10px;
		padding: 9px 14px;
		background: var(--surface-2);
		border-bottom: 1px solid var(--border);
	}
	.where {
		font-weight: 600;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	a.where {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	a.where:hover {
		color: var(--accent);
	}
	.date {
		color: var(--muted);
		font-size: 12px;
		flex: none;
	}
	.content {
		padding: 10px 14px 6px;
	}
	.meta {
		font-size: 12px;
		margin-bottom: 6px;
	}
	.stars {
		color: var(--gold);
		margin-left: 4px;
	}
	.visit {
		display: flex;
		align-items: baseline;
		gap: 8px;
		margin-bottom: 8px;
		font-size: 13px;
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
	ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	li {
		display: flex;
		gap: 8px;
		padding: 3px 0 5px;
		font-size: 13px;
	}
	.end {
		display: flex;
		flex: none;
		margin-top: 3px;
	}
	.line {
		min-width: 0;
	}
	.vintage {
		color: var(--muted);
		font-size: 12px;
	}
	.note-link {
		margin-left: 4px;
		font-size: 12px;
		color: var(--muted);
		opacity: 0.8;
	}
	.note-link:hover {
		color: var(--accent);
		opacity: 1;
	}
	.note {
		display: block;
		margin: 3px 0 2px;
		padding-left: 10px;
		border-left: 2px solid var(--border);
		color: var(--muted);
		font-style: italic;
		font-size: 12.5px;
		white-space: pre-line;
	}
	.more {
		margin-top: 12px;
	}
	.photo {
		display: block;
		max-width: min(100%, 320px);
		max-height: 240px;
		object-fit: cover;
		border-radius: 6px;
		margin-bottom: 8px;
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
