<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import type { WineDetail } from '#lib/api/details.ts';
	import { shapesUrl } from '#lib/api/details.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { links } from '#lib/links.ts';
	import CellarSection from './CellarSection.svelte';
	import DetailHeader from './DetailHeader.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import DetailMap from './DetailMap.svelte';
	import WineStyle from './WineStyle.svelte';
	import CriticScores from './CriticScores.svelte';
	import Tabs from './Tabs.svelte';
	import TastingHistory from './TastingHistory.svelte';
	import WishButton from './WishButton.svelte';
	import WineActions from './WineActions.svelte';
	import ListsPanel from './ListsPanel.svelte';
	import Icon from '#lib/components/Icon.svelte';

	interface Props {
		wine: WineDetail;
		regionColors: RegionColors;
	}

	let { wine, regionColors }: Props = $props();

	let allVintages = $state(false);
	// Add a critic's score (the header's icon): the critics card's form, shown even without any score
	let addingScore = $state(false);
	// Draw vineyard: drawn on the wine's map (DetailMap), created with its outline and linked to the wine
	let drawingVineyard = $state(false);

	const sum = (xs: { qty: number }[]) => xs.reduce((n, b) => n + b.qty, 0);
	const cellarHere = $derived(wine.cellar.filter((b) => b.wine_id === wine.id));
	const tastingsHere = $derived(wine.tastings.filter((t) => t.wine_id === wine.id));
	const cellar = $derived(allVintages ? wine.cellar : cellarHere);
	const tastings = $derived(allVintages ? wine.tastings : tastingsHere);

	const inCellar = $derived(wine.vintages.filter((v) => v.bottles));
	const tasted = $derived(wine.vintages.filter((v) => v.tastings));
	const showVintages = $derived(wine.vintages.length > 1 || inCellar.length > 0 || tasted.length > 0);

	const [drinkFrom, drinkTo] = $derived(wine.drink_window);
	// The header says the producer, cuvée, vintage, colour and region › appellation (the vineyard: on the map); this
	// line the rest:
	// its grapes (each linked), blend, disgorgement, drinking window and LWIN, whichever it has
	const grapes = $derived(wine.grapes?.length ? wine.grapes : wine.varietal ? [{ id: 0, name: wine.varietal, share: null }] : []);
	const drink = $derived(drinkFrom || drinkTo ? `${drinkFrom ?? '…'}–${drinkTo ?? '…'}` : null);
	const hasMap = $derived(!!(wine.appellation || wine.vineyard));

	// A lieu-dit clicked on the map: this wine's vineyard (and its cuvée's other vintages')
	const lieuAction = $derived({
		label: wine.vineyard ? 'Make it this wine’s vineyard instead' : 'Make it this wine’s vineyard',
		run: async (id: string) => {
			const r = await fetch(`/api/wines/${wine.id}/lieu-dit`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ lieu_dit: id })
			});
			if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Error ${r.status}`);
			await invalidateAll();
		}
	});
</script>

{#snippet title()}
	<span class="bottle"><BottleEnd region={wine.region_color} color={wine.color} size={20} /></span>
	<a class="producer" href={links.producer(wine.producer.id)}>{wine.producer.name}</a>
	<!-- Without a cuvée name the appellation is the headline -->
	{wine.cuvee || wine.appellation?.name || ''}
	<a class="muted num vintage" href={links.vintage(wine.vintage)}>{wine.vintage}</a>
{/snippet}

{#snippet actions()}
	<!-- icons, what each does on hover -->
	<a class="btn icon" href={links.editWine(wine.id)} title="Edit wine" aria-label="Edit wine"><Icon name="edit" size={15} /></a>
	{#if !wine.vineyard}<button class="btn icon" onclick={() => (drawingVineyard = true)} title="Draw its vineyard on the map" aria-label="Draw vineyard"><Icon name="draw" size={15} /></button>{/if}
	<WishButton wineId={wine.id} />
	<button class="btn icon" onclick={() => (addingScore = true)} title="Add a critic's score" aria-label="Add a critic's score"><span class="plus">+</span><Icon name="medal" size={15} /></button>
	<WineActions wineId={wine.id} actions={wine.actions} />
	<a class="btn icon" href={links.newBottle({ wine_id: wine.id })} title="Add a bottle" aria-label="Add a bottle"><span class="plus">+</span><Icon name="bottle" size={15} /></a>
	<a class="btn icon primary" href={links.newTasting({ wine_id: wine.id })} title="Add a tasting" aria-label="Add a tasting"><span class="plus">+</span><Icon name="glass" size={15} /></a>
{/snippet}

{#snippet map()}
	<!-- its vineyard in the address: a new one (linked from the map) is drawn at once -->
	<DetailMap src={`${shapesUrl('wines', wine.id)}?vineyard=${wine.vineyard?.id ?? ''}`} height={300}
		frame={wine.vineyard ? { kind: 'vineyard', id: wine.vineyard.id } : null} empty="No boundary data for this appellation." {lieuAction}
		draw={drawingVineyard ? { kind: 'vineyards', name: '', wine: wine.id } : null}
		ondrawn={(saved) => {
			drawingVineyard = false;
			if (saved) invalidateAll();
		}} />
{/snippet}

<DetailHeader
	kind={['Wine', wine.color].filter(Boolean).join(' · ')}
	{title}
	trail={[
		wine.region,
		wine.appellation && { label: wine.appellation.name, href: links.appellation(wine.appellation.id) }
	]}
	regionColor={wine.region_color}
	regionHref={wine.region ? links.region(wine.region) : null}
	{actions}
	aside={hasMap ? map : undefined}
>
	{#if grapes.length || wine.blend || wine.disgorgement_date || drink || wine.lwin}
		<p class="about">
			{#each grapes as g, i (g.name)}{#if i}, {/if}<a href={links.grape(g.name)}>{g.name}</a>{#if g.share && g.share < 100}{' '}<span class="muted num">{+g.share.toFixed(1)}%</span>{/if}{/each}
			{#if wine.blend}<span class="item">{wine.blend}</span>{/if}
			{#if wine.disgorgement_date}<span class="item">Disgorged {wine.disgorgement_date}</span>{/if}
			{#if drink}<span class="item">Drink <span class="num">{drink}</span>{#if wine.maturity}{' '}<MaturityBadge maturity={wine.maturity} />{/if}</span>{/if}
			{#if wine.lwin}<span class="item muted">LWIN <a class="num" href={links.winelabs(wine.lwin, wine.vintage)} target="_blank" rel="noreferrer">{wine.lwin} ↗</a></span>{/if}
		</p>
	{/if}
	<WineStyle wineId={wine.id} tags={wine.tags ?? []} cuvee={wine.cuvee_tags ?? []} />
</DetailHeader>

<div class="row">
		<CriticScores wineId={wine.id} scores={wine.scores} bind:adding={addingScore} />
		{#if showVintages}
			<section class="card vintages">
				<h2>Vintages <span class="muted num">{wine.vintages.length}</span>
					{#if wine.cuvee_lists?.length}<span class="listed any" title="Any vintage on: {wine.cuvee_lists.join(', ')}"><Icon name="bookmark" size={12} /> any vintage on {wine.cuvee_lists.join(', ')}</span>{/if}
				</h2>
				<div class="chips">
					{#each wine.vintages as v (v.id)}
						<a
							class="chip num"
							class:current={v.id === wine.id}
							class:owned={v.bottles > 0}
							href={links.wine(v.id)}
							title={[v.bottles && `${v.bottles} in cellar`, v.tastings && `tasted ${v.tastings}×`, v.scores, v.lists?.length && `on ${v.lists.join(', ')}`].filter(Boolean).join(' · ') || undefined}
						>
							{v.vintage}{#if v.bottles}<span class="n">{v.bottles}</span>{/if}{#if v.tastings}<span class="tick">✓</span>{/if}{#if v.score}<span class="score">{v.score}</span>{/if}{#if v.lists?.length}<span class="listed"><Icon name="bookmark" size={11} /></span>{/if}
						</a>
					{/each}
				</div>
				<dl>
					{#if inCellar.length}<dt>In cellar</dt><dd>{inCellar.map((v) => v.vintage).join(', ')}</dd>{/if}
					{#if tasted.length}<dt>Tasted</dt><dd>{tasted.map((v) => v.vintage).join(', ')}</dd>{/if}
				</dl>
			</section>
		{/if}
	</div>

<ListsPanel wineId={wine.id} />

<Tabs
	tabs={[
		{ id: 'cellar', label: 'Cellar', count: sum(cellar) },
		{ id: 'history', label: 'History', count: tastings.length }
	]}
	initial={!cellarHere.length && tastingsHere.length ? 'history' : 'cellar'}
>
	{#snippet tools()}
		{#if wine.vintages.length > 1}
			<div class="seg">
				<button class:on={!allVintages} onclick={() => (allVintages = false)}>This vintage</button>
				<button class:on={allVintages} onclick={() => (allVintages = true)}>All vintages</button>
			</div>
		{/if}
	{/snippet}
	{#snippet children(tab)}
		{#if tab === 'cellar'}
			<CellarSection
				bottles={cellar}
				{regionColors}
				empty={allVintages ? 'No bottles of any vintage in stock.' : 'No bottles of this vintage in stock.'}
			/>
		{:else}
			<TastingHistory
				{tastings}
				{regionColors}
				empty={allVintages ? 'No tasting notes for any vintage.' : 'No tasting notes for this vintage.'}
			/>
		{/if}
	{/snippet}
</Tabs>

<style>
	/* the grapes, blend, disgorgement, drinking window, LWIN: one line under the header's */
	.about {
		margin: 0 0 10px;
		font-size: 14px;
		line-height: 1.6;
	}
	.about a {
		color: inherit;
	}
	.about a:hover {
		color: var(--accent);
	}
	.about .item::before {
		content: '·';
		margin: 0 8px;
		color: var(--muted);
	}
	.about > .item:first-child::before {
		content: none;
		margin: 0;
	}
	.bottle {
		display: inline-block;
		margin-right: 8px;
		transform: translateY(-2px);
	}
	.producer:hover,
	.vintage:hover {
		color: var(--accent);
	}
	.row {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
		gap: 14px;
		margin-bottom: 14px;
	}
	.row > .card {
		padding: 14px 18px;
	}
	h2 {
		font-size: 14px;
		margin: 0 0 10px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 1px 9px;
		border-radius: 10px;
		border: 1px solid var(--border);
		font-size: 12px;
	}
	.chip:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
	.chip.owned {
		border-color: var(--gold);
	}
	.chip.current {
		background: var(--accent);
		border-color: var(--accent);
		color: white;
	}
	.chip.current .n,
	.chip.current .tick,
	.chip.current .listed {
		color: white;
	}
	/* the score's pill on the selected vintage: white, as its other marks */
	.chip.current .score {
		color: white;
		border-color: rgba(255, 255, 255, 0.7);
	}
	.n {
		font-weight: 650;
		color: var(--gold);
	}
	.score {
		margin-left: 4px;
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
		align-items: center;
		gap: 4px;
		margin-left: 4px;
		color: var(--accent);
	}
	.listed :global(.icon) {
		fill: currentColor;
	}
	.listed.any {
		font-size: 12px;
		font-weight: 400;
		margin-left: 10px;
	}
	.tick {
		color: var(--accent);
		font-size: 11px;
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 4px 12px;
		margin: 12px 0 0;
		font-size: 13px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
	}
	.seg button {
		padding: 4px 10px;
		font-size: 12px;
	}
</style>
