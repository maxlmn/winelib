<script lang="ts">
	import type { CatalogEntry } from '#lib/api/details.ts';
	import { typeColor } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';

	interface Props {
		wines: CatalogEntry[];
		/** list the producer on each line (pages that aren't a producer's) */
		showProducer?: boolean;
	}

	let { wines, showProducer = false }: Props = $props();

	// Vintages neither in the cellar nor tasted (known only from a critic's review): hidden until asked for
	const seen = (v: CatalogEntry['vintages'][number]) => v.bottles > 0 || v.tastings > 0;
	const unseen = $derived(wines.reduce((n, w) => n + w.vintages.filter((v) => !seen(v)).length, 0));
	let showAll = $state(false);
	const shown = $derived(
		showAll ? wines : wines.map((w) => ({ ...w, vintages: w.vintages.filter(seen) })).filter((w) => w.vintages.length)
	);
</script>

{#if !wines.length}
	<p class="muted">No wines recorded.</p>
{:else}
	<p class="legend muted">
		<span class="chip owned sample">n</span> bottles in cellar
		<span class="chip tasted sample">✓</span> tasted
		{#if unseen}
			<span class="chip sample">–</span> neither (a review only)
			<label class="toggle">
				<input type="checkbox" bind:checked={showAll} />
				Show {unseen} not owned, not tasted
			</label>
		{/if}
	</p>
	{#if !shown.length}<p class="muted">Nothing owned or tasted: tick the box above to see the {unseen} known from reviews.</p>{/if}
	<ul>
		{#each shown as w (`${w.producer_id}|${w.cuvee}|${w.appellation?.id}|${w.varietal}`)}
			<!-- The line under the headline: the appellation and grape it doesn't already show -->
			{@const appInSub = !!(w.cuvee && w.appellation)}
			{@const grapeInSub = !!(w.varietal && (w.cuvee || w.appellation))}
			<li>
				<div class="name">
					<span class="dot" style:background={typeColor(w.color)}></span>
					<div>
						{#if showProducer}<a class="producer" href={links.producer(w.producer_id)}>{w.producer}</a>{/if}
						<!-- Without a cuvée name the appellation is the headline (then the grape, then the color) -->
						{#if w.cuvee}
							<b>{w.cuvee}</b>
						{:else if w.appellation}
							<b><a href={links.appellation(w.appellation.id)}>{w.appellation.name}</a></b>
						{:else}
							<b>{w.varietal ?? w.color ?? ''}</b>
						{/if}
						{#if appInSub || grapeInSub}
							<div class="sub muted">
								{#if appInSub && w.appellation}<a href={links.appellation(w.appellation.id)}>{w.appellation.name}</a>{/if}
								{#if appInSub && grapeInSub}·{/if}
								{#if grapeInSub && w.varietal}<a href={links.grape(w.varietal)}>{w.varietal}</a>{/if}
							</div>
						{/if}
					</div>
				</div>
				<div class="vintages">
					{#each w.vintages as v (v.id)}
						<a
							class="chip num"
							class:owned={v.bottles > 0}
							class:tasted={v.tastings > 0}
							href={links.wine(v.id)}
							title={[v.bottles && `${v.bottles} in cellar`, v.tastings && `tasted ${v.tastings}×`, v.scores].filter(Boolean).join(' · ') || 'Not in cellar, not tasted'}
						>
							{v.vintage}
							{#if v.bottles}<span class="n">{v.bottles}</span>{/if}
							{#if v.tastings}<span class="tick">✓</span>{/if}
						</a>
					{/each}
				</div>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.legend {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		margin: 0 0 10px;
	}
	.legend .sample {
		margin-left: 8px;
	}
	.toggle {
		margin-left: auto;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		cursor: pointer;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: grid;
		grid-template-columns: minmax(200px, 1fr) minmax(0, 2fr);
		gap: 6px 16px;
		padding: 9px 0;
		border-top: 1px solid var(--border);
	}
	li:first-child {
		border-top: none;
	}
	.name {
		display: flex;
		align-items: baseline;
		gap: 8px;
		min-width: 0;
	}
	.producer {
		margin-right: 4px;
	}
	.sub {
		font-size: 12px;
	}
	.sub a:hover,
	.producer:hover {
		color: var(--accent);
	}
	.vintages {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		align-content: flex-start;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 1px 8px;
		border-radius: 10px;
		border: 1px solid var(--border);
		font-size: 12px;
		color: var(--muted);
	}
	.chip:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.chip.tasted {
		color: var(--text);
		background: var(--surface-2);
	}
	.chip.owned {
		color: var(--text);
		border-color: var(--gold);
	}
	.n {
		font-weight: 650;
		color: var(--gold);
	}
	.tick {
		color: var(--accent);
		font-size: 11px;
	}
	@media (max-width: 640px) {
		li {
			grid-template-columns: 1fr;
		}
	}
</style>
