<script lang="ts">
	import PlaceName from '#lib/components/PlaceName.svelte';
	import { isFriends } from '#lib/places.ts';
	import { accentColor } from '#lib/theme.svelte.ts';
	import type { Place, Tasting, Visit } from '#lib/api/tastings.ts';
	import PointMap from '#lib/components/PointMap.svelte';
	import type { MapPoint } from '#lib/components/PointMap.svelte';
	import { typeColor } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';
	import { fmtDay, stars } from './journal.ts';

	interface Props {
		tastings: Tasting[];
		visits: Visit[];
		places: Record<string, Place>;
		selected: number | null;
		onselect: (id: number | null) => void;
		/** narrow the whole page to this place */
		onfilter: (name: string) => void;
	}

	let { tastings, visits, places, selected, onselect, onfilter }: Props = $props();

	const LIST_LIMIT = 200;

	interface Row {
		place: Place;
		wines: Tasting[];
		visits: Visit[];
		days: number;
	}

	// Places in the current selection, each with its tastings and visits (one visit counts as one event)
	const rows = $derived.by(() => {
		const byPlace = new Map<number, Row>();
		const row = (id: number) => {
			if (!byPlace.has(id)) byPlace.set(id, { place: places[id], wines: [], visits: [], days: 0 });
			return byPlace.get(id)!;
		};
		for (const t of tastings) if (t.place_id && places[t.place_id]) row(t.place_id).wines.push(t);
		for (const v of visits) if (places[v.place_id]) row(v.place_id).visits.push(v);
		for (const r of byPlace.values()) r.days = new Set([...r.wines, ...r.visits].map((x) => x.date)).size;
		return [...byPlace.values()].sort((a, b) => b.wines.length + b.visits.length - a.wines.length - a.visits.length || a.place.name.localeCompare(b.place.name));
	});
	const located = $derived(rows.filter((r) => r.place.lat !== null && r.place.lng !== null));
	const unlocated = $derived(rows.length - located.length);

	const summary = (r: Row) =>
		[r.wines.length && plural(r.wines.length, 'wine'), plural(r.days, 'occasion')].filter(Boolean).join(' · ');

	const points = $derived<MapPoint[]>(
		located.map((r) => ({
			id: r.place.id,
			lat: r.place.lat!,
			lng: r.place.lng!,
			label: `${r.place.name}${r.place.stars ? ` ${stars(r.place.stars)}` : ''}`,
			sub: [r.place.city, summary(r)].filter(Boolean).join(' · '),
			color: r.wines.length ? accentColor() : '#d4af37',
			weight: r.wines.length + r.visits.length
		}))
	);

	const current = $derived(rows.find((r) => r.place.id === selected) ?? null);
	const days = $derived.by(() => {
		if (!current) return [];
		const byDay = new Map<string, { wines: Tasting[]; visit?: Visit }>();
		// Rows come newest first, in tasting order within a day
		for (const t of current.wines) byDay.set(t.date, { wines: [...(byDay.get(t.date)?.wines ?? []), t] });
		for (const v of current.visits) byDay.set(v.date, { wines: byDay.get(v.date)?.wines ?? [], visit: v });
		return [...byDay].sort(([a], [b]) => b.localeCompare(a));
	});
</script>

<div class="layout">
	<div class="map card">
		<PointMap {points} selectedId={selected} {onselect} zoom={13} />
		{#if !points.length}
			<div class="empty card">No geocoded places in the current selection.</div>
		{/if}
	</div>
	<aside class="card">
		{#if current}
			{@const p = current.place}
			<div class="detail">
				<button class="close" onclick={() => onselect(null)} aria-label="Close">✕</button>
				<div class="kind">{isFriends(p.type) ? "A friend's home" : (p.type ?? 'Place')}</div>
				<h3><PlaceName name={p.name} type={p.type} /> {#if p.stars}<span class="stars">{stars(p.stars)}</span>{/if}</h3>
				<p class="muted">{[p.city, p.country].filter(Boolean).join(', ')}</p>
				<p class="num">{summary(current)}{current.visits.length ? ` · ${plural(current.visits.length, 'visit')}` : ''}</p>
				<div class="links">
					<button class="link" onclick={() => onfilter(p.name)}>Only this place</button>
					<a href={links.newTasting({ place_id: p.id })}>+ Tasting</a>
					<a href={links.place(p.id)}>Details →</a>
				</div>
				{#if p.lat === null}<p class="muted hint">No coordinates for this place.</p>{/if}
			</div>
			<div class="list">
				{#each days as [day, d] (day)}
					<div class="day">
						<div class="day-h num">{fmtDay(day)}{#if d.visit && !d.wines.length}<span class="muted"> · visit</span>{/if}</div>
						{#each d.wines as w (w.id)}
							<a class="wine" href={links.tasting(w.id)} title={w.notes || undefined}>
								<span class="dot" style:background={typeColor(w.color)}></span>
								<span><b>{w.producer}</b>{w.cuvee ? ` ${w.cuvee}` : ''} <span class="muted num">{w.vintage}</span></span>
							</a>
						{/each}
						{#if d.visit?.notes}<p class="visit muted">{d.visit.notes}</p>{/if}
					</div>
				{/each}
			</div>
		{:else}
			<div class="list-h">
				<b>{plural(rows.length, 'place')}</b>
				<span class="muted">Click one, here or on the map</span>
			</div>
			<div class="list">
				{#each rows.slice(0, LIST_LIMIT) as r (r.place.id)}
					<button class="row" onclick={() => onselect(r.place.id)}>
						<span class="name"><PlaceName name={r.place.name} type={r.place.type} />{#if r.place.stars} <span class="stars">{stars(r.place.stars)}</span>{/if}</span>
						<span class="muted city">{r.place.city ?? ''}</span>
						<span class="badge num">{r.wines.length || '·'}</span>
					</button>
				{/each}
				{#if rows.length > LIST_LIMIT}<p class="muted hint">{rows.length - LIST_LIMIT} more: filter to narrow down</p>{/if}
				{#if unlocated}<p class="muted hint">{plural(unlocated, 'place')} without coordinates (not on the map)</p>{/if}
			</div>
		{/if}
	</aside>
</div>

<style>
	.layout {
		display: grid;
		grid-template-columns: 1fr 320px;
		gap: 14px;
		height: max(480px, calc(100vh - 330px));
	}
	.map {
		position: relative;
		overflow: hidden;
		box-shadow: none;
	}
	.empty {
		position: absolute;
		left: 50%;
		top: 50%;
		transform: translate(-50%, -50%);
		padding: 12px 16px;
	}
	aside {
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: hidden;
		box-shadow: none;
	}
	.list-h {
		display: flex;
		flex-direction: column;
		padding: 12px 14px 8px;
		border-bottom: 1px solid var(--border);
		font-size: 13px;
	}
	.list-h span {
		font-size: 12px;
	}
	.list {
		overflow-y: auto;
		flex: 1;
		padding: 6px;
	}
	.row {
		display: grid;
		grid-template-columns: 1fr auto;
		grid-template-areas: 'name badge' 'city badge';
		align-items: center;
		width: 100%;
		text-align: left;
		border: none;
		background: none;
		padding: 5px 8px;
		border-radius: 6px;
		cursor: pointer;
		column-gap: 8px;
	}
	.row:hover {
		background: var(--surface-2);
	}
	.name {
		grid-area: name;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.city {
		grid-area: city;
		font-size: 12px;
	}
	.badge {
		grid-area: badge;
		font-size: 11px;
		padding: 1px 7px;
		border-radius: 10px;
		background: var(--accent-soft);
		color: var(--accent);
	}
	.stars {
		color: var(--gold);
		font-size: 11px;
		letter-spacing: 1px;
	}
	.detail {
		position: relative;
		padding: 14px;
		border-bottom: 1px solid var(--border);
		background: var(--surface-2);
	}
	.detail p {
		margin: 2px 0;
		font-size: 13px;
	}
	.kind {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted);
	}
	h3 {
		margin: 2px 24px 2px 0;
		font-size: 16px;
	}
	.close {
		position: absolute;
		right: 10px;
		top: 10px;
		border: none;
		background: none;
		color: var(--muted);
		cursor: pointer;
	}
	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
		margin-top: 8px;
		font-size: 13px;
	}
	.links a,
	.link {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.links a:hover, .link:hover {
		color: var(--accent);
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		cursor: pointer;
	}
	.day {
		padding: 6px 8px;
	}
	.day-h {
		font-size: 12px;
		font-weight: 600;
		color: var(--muted);
		margin-bottom: 2px;
	}
	.wine {
		display: flex;
		align-items: baseline;
		gap: 7px;
		padding: 2px 0;
		font-size: 13px;
	}
	.wine .dot {
		width: 8px;
		height: 8px;
	}
	.visit {
		margin: 2px 0;
		font-size: 12px;
		font-style: italic;
	}
	.hint {
		font-size: 12px;
		padding: 4px 8px;
	}
	@media (max-width: 900px) {
		.layout {
			grid-template-columns: 1fr;
			height: auto;
		}
		.map {
			height: 380px;
		}
		aside {
			max-height: 420px;
		}
	}
</style>
