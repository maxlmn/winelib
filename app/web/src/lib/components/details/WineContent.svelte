<script lang="ts">
	import { grapesText } from '#lib/grapes.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import type { WineDetail } from '#lib/api/details.ts';
	import { shapesUrl } from '#lib/api/details.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { links } from '#lib/links.ts';
	import { TYPE_COLORS } from '#lib/colors.ts';
	import CellarSection from './CellarSection.svelte';
	import DetailHeader from './DetailHeader.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import DetailMap from './DetailMap.svelte';
	import Facts from './Facts.svelte';
	import CriticScores from './CriticScores.svelte';
	import Tabs from './Tabs.svelte';
	import TastingHistory from './TastingHistory.svelte';
	import WishButton from './WishButton.svelte';

	interface Props {
		wine: WineDetail;
		regionColors: RegionColors;
	}

	let { wine, regionColors }: Props = $props();

	let allVintages = $state(false);

	const sum = (xs: { qty: number }[]) => xs.reduce((n, b) => n + b.qty, 0);
	const cellarHere = $derived(wine.cellar.filter((b) => b.wine_id === wine.id));
	const tastingsHere = $derived(wine.tastings.filter((t) => t.wine_id === wine.id));
	const cellar = $derived(allVintages ? wine.cellar : cellarHere);
	const tastings = $derived(allVintages ? wine.tastings : tastingsHere);

	const inCellar = $derived(wine.vintages.filter((v) => v.bottles));
	const tasted = $derived(wine.vintages.filter((v) => v.tastings));
	const showVintages = $derived(wine.vintages.length > 1 || inCellar.length > 0 || tasted.length > 0);

	const [drinkFrom, drinkTo] = $derived(wine.drink_window);
	const facts = $derived([
		{ label: 'Producer', value: wine.producer.name, href: links.producer(wine.producer.id), icon: 'person' as const },
		{ label: 'Region', value: regionLabel(wine.region), dot: regionColor(wine.region), href: wine.region ? links.region(wine.region) : null, icon: 'globe' as const },
		{ label: 'Type', value: wine.color, dot: TYPE_COLORS[wine.color ?? ''] },
		{ label: 'Disgorged', value: wine.disgorgement_date },
		{ label: 'Appellation', value: wine.appellation?.name ?? 'N/A', href: wine.appellation && links.appellation(wine.appellation.id), icon: 'map' as const },
		{ label: 'Vineyard', value: wine.vineyard?.label, href: wine.vineyard && links.vineyard(wine.vineyard.id) },
		// one grape: a link to its page; several: listed, each linked below the facts
		{ label: (wine.grapes?.length ?? 0) > 1 ? 'Grapes' : 'Grape', value: grapesText(wine.grapes, wine.varietal) ?? 'N/A',
			href: (wine.grapes?.length ?? 0) <= 1 && wine.varietal ? links.grape(wine.varietal) : null, icon: 'grape' as const },
		{ label: 'Blend', value: wine.blend },
		{ label: 'Drink', value: drinkFrom || drinkTo ? `${drinkFrom ?? '…'} – ${drinkTo ?? '…'}` : null, maturity: wine.maturity },
		{ label: 'LWIN', value: wine.lwin, href: wine.lwin && links.winelabs(wine.lwin, wine.vintage) }
	]);
	const hasMap = $derived(!!(wine.appellation || wine.vineyard));
</script>

{#snippet title()}
	<span class="bottle"><BottleEnd region={wine.region_color} color={wine.color} size={20} /></span>
	<a class="producer" href={links.producer(wine.producer.id)}>{wine.producer.name}</a>
	<!-- Without a cuvée name the appellation is the headline -->
	{wine.cuvee || wine.appellation?.name || ''}
	<a class="muted num vintage" href={links.vintage(wine.vintage)}>{wine.vintage}</a>
{/snippet}

{#snippet actions()}
	<a class="btn" href={links.editWine(wine.id)}>Edit wine</a>
	{#if !wine.vineyard}<a class="btn" href={links.newVineyard(wine.id)}>Draw vineyard</a>{/if}
	<WishButton wineId={wine.id} item={wine.wishlist} />
	<a class="btn" href={links.newBottle({ wine_id: wine.id })}>＋ Bottle</a>
	<a class="btn primary" href={links.newTasting({ wine_id: wine.id })}>＋ Tasting</a>
{/snippet}

{#snippet map()}
	<DetailMap src={shapesUrl('wines', wine.id)} height={300} focusable empty="No boundary data for this appellation." />
{/snippet}

<DetailHeader
	kind={['Wine', wine.color].filter(Boolean).join(' · ')}
	{title}
	trail={[wine.region, wine.appellation?.name]}
	regionColor={wine.region_color}
	regionHref={wine.region ? links.region(wine.region) : null}
	{actions}
	aside={hasMap ? map : undefined}
>
	<Facts items={facts} />
</DetailHeader>

<div class="row">
		<CriticScores wineId={wine.id} scores={wine.scores} actions={wine.actions} />
		{#if showVintages}
			<section class="card vintages">
				<h2>Vintages <span class="muted num">{wine.vintages.length}</span></h2>
				<div class="chips">
					{#each wine.vintages as v (v.id)}
						<a
							class="chip num"
							class:current={v.id === wine.id}
							class:owned={v.bottles > 0}
							href={links.wine(v.id)}
							title={[v.bottles && `${v.bottles} in cellar`, v.tastings && `tasted ${v.tastings}×`].filter(Boolean).join(' · ') || undefined}
						>
							{v.vintage}{#if v.bottles}<span class="n">{v.bottles}</span>{/if}{#if v.tastings}<span class="tick">✓</span>{/if}
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
	.chip.current .tick {
		color: white;
	}
	.n {
		font-weight: 650;
		color: var(--gold);
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
