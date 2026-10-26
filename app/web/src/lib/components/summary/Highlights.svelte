<script lang="ts">
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import PlaceName from '#lib/components/PlaceName.svelte';
	import BarList from './BarList.svelte';
	import type { CellarSummary, HighlightWine, TastingSummary } from '#lib/api/summary.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { fmtDate } from '#lib/components/details/wine.ts';
	import { links } from '#lib/links.ts';
	import { plural } from '#lib/format.ts';

	/** The personal part of the summary: tastings (best scored, most visited, busiest evening) or the cellar
	 * (largest holdings, oldest vintages, storage) */
	let { tastings, cellar }: { tastings?: TastingSummary['highlights']; cellar?: CellarSummary['highlights'] } = $props();

	const EVENING = 4; // wines named on the busiest evening's card, the others as bottle ends only
	const name = (w: HighlightWine) => `${w.producer}${w.cuvee ? ` – ${w.cuvee}` : ''}`;
</script>

{#snippet wine(w: HighlightWine, href: string, side: string)}
	<li>
		<span class="end">
			<BottleEnd region={regionColor(w.region)} color={w.color} format={w.format} size={11} title="{regionLabel(w.region)} · {w.color ?? ''}" />
		</span>
		<a class="name" {href}>{name(w)} <span class="muted num">{w.vintage}</span></a>
		<span class="side num">{side}</span>
	</li>
{/snippet}

<div class="highlights">
	{#if tastings}
		<section class="card">
			<h2>Your best scored</h2>
			{#if tastings.best.length}
				<ul>{#each tastings.best as w (w.wine_id)}{@render wine(w, links.tasting(w.id), String(w.rating))}{/each}</ul>
			{:else}
				<p class="muted">Score a tasting and it shows here.</p>
			{/if}
		</section>
		<section class="card">
			<h2>Most visited</h2>
			<ul>
				{#each tastings.places as p (p.id)}
					<li>
						<a class="name" href={links.place(p.id)}><PlaceName name={p.name} type={p.type} />{#if p.city}<span class="muted">{' · '}{p.city}</span>{/if}</a>
						<span class="side num">{plural(p.visits, 'day')}</span>
					</li>
				{:else}
					<li class="muted">No places yet.</li>
				{/each}
			</ul>
		</section>
		<section class="card">
			<h2>Busiest evening</h2>
			{#if tastings.evening}
				{@const e = tastings.evening}
				<div class="evening muted">
					{#if e.place_id}<a href={links.place(e.place_id)}>{e.place}</a>{:else}{e.place ?? ''}{/if} · {fmtDate(e.date)} ·
					{plural(e.wines.length, 'wine')}
				</div>
				<!-- The whole evening as bottle ends, in the order poured; the first wines named below -->
				<div class="poured">
					{#each e.wines as w (w.id)}
						<a href={links.tasting(w.id)}>
							<BottleEnd region={regionColor(w.region)} color={w.color} format={w.format} size={14} title="{name(w)} {w.vintage}" />
						</a>
					{/each}
				</div>
				<ul>{#each e.wines.slice(0, EVENING) as w, i (w.id)}{@render wine(w, links.tasting(w.id), String(i + 1))}{/each}</ul>
				{#if e.wines.length > EVENING}<div class="more muted">and {e.wines.length - EVENING} more</div>{/if}
			{:else}
				<p class="muted">No evenings yet.</p>
			{/if}
		</section>
	{:else if cellar}
		<section class="card">
			<h2>Largest holdings</h2>
			<ul>{#each cellar.largest as w (w.wine_id)}{@render wine(w, links.wine(w.wine_id), `×${w.qty}`)}{/each}</ul>
		</section>
		<section class="card">
			<h2>Oldest vintages</h2>
			{#if cellar.oldest.length}
				<ul>{#each cellar.oldest as w (w.wine_id)}{@render wine(w, links.wine(w.wine_id), `×${w.qty}`)}{/each}</ul>
			{:else}
				<p class="muted">No dated bottles.</p>
			{/if}
		</section>
		<section class="card">
			<h2>By storage</h2>
			<BarList
				bars={cellar.storage.map((s) => ({ key: s.name, label: s.name, count: s.count, color: 'var(--accent)' }))}
				total={cellar.storage.reduce((n, s) => n + s.count, 0)}
				unit="bottles"
			/>
		</section>
	{/if}
</div>

<style>
	.highlights {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 14px;
		margin-bottom: 14px;
	}
	section {
		padding: 14px 16px 16px;
	}
	h2 {
		font-size: 14px;
		margin: 0 0 10px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 7px;
	}
	li {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		min-width: 0;
	}
	.end {
		display: flex;
		flex: none;
	}
	.name {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.side {
		flex: none;
		color: var(--muted);
		font-size: 12px;
	}
	.evening {
		font-size: 12px;
		margin: -4px 0 10px;
	}
	.poured {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 3px;
		margin-bottom: 10px;
	}
	.poured a {
		display: flex;
	}
	.more {
		font-size: 12px;
		margin-top: 7px;
	}
	@media (max-width: 900px) {
		.highlights {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
