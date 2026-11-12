<script lang="ts">
	import type { CatalogEntry } from '#lib/api/details.ts';
	import { typeColor } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { appSettings } from '#lib/settings.svelte.ts';
	import LabelThumbs from './LabelThumbs.svelte';
	import { SvelteSet } from 'svelte/reactivity';

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
	// a column of labels at the right when any line has one (empty on the others: the columns line up)
	// a cuvée's vintages folded into one line ("13 vintages · 2008–2017 · 7 bottles · 12 tasted"), a click opens them
	const keyOf = (w: CatalogEntry) => `${w.producer_id}|${w.cuvee}|${w.appellation?.id}|${w.varietal}`;
	const opened = new SvelteSet<string>();
	const toggle = (key: string) => (opened.has(key) ? opened.delete(key) : opened.add(key));
	function summary(vs: CatalogEntry['vintages']) {
		const years = vs.map((v) => v.vintage).filter((y) => /^\d{4}/.test(y)).map((y) => y.slice(0, 4)).sort();
		const bottles = vs.reduce((n, v) => n + v.bottles, 0);
		const tasted = vs.filter((v) => v.tastings > 0).length;
		return {
			count: `${vs.length} ${vs.length === 1 ? 'vintage' : 'vintages'}`,
			range: years.length > 1 && years[0] !== years.at(-1) ? `${years[0]}–${years.at(-1)}` : (years[0] ?? vs[0]?.vintage ?? ''),
			bottles,
			tasted
		};
	}
	const withLabels = $derived(appSettings.wine_labels !== 'off' && shown.some((w) => w.labels?.length));
</script>

{#if !wines.length}
	<p class="muted">No wines recorded.</p>
{:else}
	<p class="legend muted">
		<span class="item"><span class="chip owned sample">n</span> bottles in cellar</span>
		<span class="item"><span class="chip tasted sample">✓</span> tasted</span>
		<span class="item"><span class="chip sample"><span class="score">94</span></span> critic</span>
		<span class="item"><span class="chip sample"><span class="listed"><Icon name="bookmark" size={11} /></span></span> on a list</span>
		{#if unseen}
			<span class="item"><span class="chip sample">–</span> neither (a review only)</span>
			<label class="toggle">
				<input type="checkbox" bind:checked={showAll} />
				Show {unseen} not owned, not tasted
			</label>
		{/if}
	</p>
	{#if !shown.length}<p class="muted">Nothing owned or tasted: tick the box above to see the {unseen} known from reviews.</p>{/if}
	<ul>
		{#each shown as w (keyOf(w))}
			{@const open = opened.has(keyOf(w))}
			{@const sum = summary(w.vintages)}
			<!-- The line under the headline: the appellation and grape it doesn't already show -->
			{@const appInSub = !!(w.cuvee && w.appellation)}
			{@const grapeInSub = !!(w.varietal && (w.cuvee || w.appellation))}
			<li class:with-labels={withLabels}>
				<div class="name">
					<span class="dot" style:background={typeColor(w.color)}></span>
					<div>
						{#if showProducer}<a class="producer" href={links.producer(w.producer_id)}>{w.producer}</a>{/if}
						<!-- Without a cuvée name the appellation is the headline (then the grape, then the color) -->
						{#if w.lists?.length}<span class="listed" title="Any vintage on: {w.lists.join(', ')}"><Icon name="bookmark" size={12} /></span>{/if}
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
				<div class="vintages-cell">
					<button type="button" class="fold" aria-expanded={open} onclick={() => toggle(keyOf(w))}>
						<!-- two lines, beside the name's two: which vintages, then what's in the cellar and tasted -->
						<span class="what">{sum.count}{#if sum.range}<span class="muted num">{` · ${sum.range}`}</span>{/if}</span>
						<span class="chev" aria-hidden="true">{open ? '▴' : '▾'}</span>
						<span class="had">
							{#if sum.bottles}<span class="n num">{sum.bottles} {sum.bottles === 1 ? 'bottle' : 'bottles'}</span>{/if}
							{#if sum.bottles && sum.tasted}<span class="muted"> · </span>{/if}
							{#if sum.tasted}<span class="tick">{sum.tasted} tasted</span>{/if}
						</span>
					</button>
					{#if open}
				<div class="vintages">
					{#each w.vintages as v (v.id)}
						<a
							class="chip num"
							class:owned={v.bottles > 0}
							class:tasted={v.tastings > 0}
							href={links.wine(v.id)}
							title={[v.bottles && `${v.bottles} in cellar`, v.tastings && `tasted ${v.tastings}×`, v.scores, v.lists?.length && `on ${v.lists.join(', ')}`].filter(Boolean).join(' · ') || 'Not in cellar, not tasted'}
						>
							<!-- each mark in its slot, empty or not: they line up from pill to pill -->
							<span>{v.vintage}</span>
							<span class="n">{v.bottles || ''}</span>
							<span class="tick">{v.tastings ? '✓' : ''}</span>
							<span class="marks">
								{#if v.score}<span class="score">{v.score}</span>{/if}
								{#if v.lists?.length}<span class="listed"><Icon name="bookmark" size={11} /></span>{/if}
							</span>
						</a>
					{/each}
				</div>
					{/if}
				</div>
				<!-- its uploaded labels, small, side by side in a strip slid left and right (Settings > Labels: none, none here either) -->
				{#if withLabels}
					<div class="labels">
						{#if w.labels?.length}<LabelThumbs labels={w.labels} name={w.cuvee || w.appellation?.name || w.producer} carousel />{/if}
					</div>
				{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	/* wraps on a narrow screen, each sample beside its words */
	.legend {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px 14px;
		font-size: 12px;
		margin: 0 0 10px;
	}
	.legend .item {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		white-space: nowrap;
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
	/* the labels' column, at the right: two side by side, more slid in (a carousel) */
	li.with-labels {
		grid-template-columns: minmax(140px, 1fr) minmax(0, 2fr) 134px;
	}
	.labels {
		display: flex;
		justify-content: flex-end;
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
	/* the vintages folded: one line saying how many, which years, bottles and tastings; a click opens them */
	.fold {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: baseline;
		gap: 0 10px;
		width: 100%;
		padding: 3px 0;
		border: none;
		background: none;
		font: inherit;
		font-size: 13px;
		color: var(--text);
		text-align: left;
		cursor: pointer;
	}
	.fold:hover {
		color: var(--accent);
	}
	.had {
		grid-column: 1 / -1;
		font-size: 12px;
	}
	.chev {
		color: var(--muted);
	}
	.vintages-cell .vintages {
		margin-top: 6px;
	}
	/* the vintages in one column, newest first: pills of one width, the years and their marks in line */
	.vintages {
		display: grid;
		grid-template-columns: 132px;
		gap: 4px;
	}
	/* a pill: the year, then its bottles, its tick and its score (and list mark), each in its slot */
	.vintages .chip {
		display: grid;
		grid-template-columns: 1fr 14px 10px 40px;
		gap: 3px;
	}
	.vintages .n {
		text-align: right;
	}
	.marks {
		display: inline-flex;
		align-items: center;
		justify-content: flex-end;
		gap: 2px;
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
		border-color: var(--gold-text);
	}
	.n {
		font-weight: 650;
		color: var(--gold-text);
	}
	.tick {
		color: var(--accent);
		font-size: 11px;
	}
	/* the preferred critic's score, a pill like the lists' */
	.score {
		font-size: 10px;
		font-weight: 600;
		line-height: 13px;
		padding: 0 4px;
		border-radius: 6px;
		border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
		color: var(--accent);
	}
	.listed {
		display: inline-flex;
		color: var(--accent);
	}
	.listed :global(.icon) {
		fill: currentColor;
	}
	/* a phone: the name, then the vintages and the labels' column */
	@media (max-width: 640px) {
		li {
			grid-template-columns: 1fr;
		}
		li.with-labels {
			grid-template-columns: minmax(0, 1fr) 134px;
		}
		li.with-labels .name {
			grid-column: 1 / -1;
		}
	}
</style>
