<script lang="ts">
	/** A detail page's Cellar tab (a wine's, a bottle's, a producer's, an appellation's...): its bottles as plain
	 * lines, each saying where it is. No card per storage place (the Cellar page has those: CellarCards). */
	import CriticPills from '#lib/components/CriticPills.svelte';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import LabelThumbs from './LabelThumbs.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Bottle, RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { appSettings } from '#lib/settings.svelte.ts';
	import { symbol } from '#lib/format.ts';
	import { fmtDate } from './wine.ts';

	interface Props {
		bottles: Bottle[];
		regionColors: RegionColors;
		empty?: string;
		/** one wine's bottles: its lines as they are (kept for its callers; the lines are the same) */
		plain?: boolean;
		/** the bottle whose page this is: its line marked */
		current?: number | null;
		/** purchases (the home page's recent ones): in the order given, each with its price paid a bottle, its day
		 * and where it was bought, in place of where it's kept */
		prices?: boolean;
		/** the wines' labels (a producer's page): each line's, small, opening larger */
		labels?: Record<number, { url: string; from_vintage: string | null }>;
	}

	let { bottles, regionColors, empty = 'Nothing in the cellar.', current = null, prices = false, labels = {} }: Props = $props();
	const paid = (b: Bottle) => (b.price ? `${symbol(b.currency ?? appSettings.currency)}${Math.round(b.price).toLocaleString()}` : null);

	const PAGE = 60;
	let limit = $state(PAGE);

	const lines = $derived(
		prices ? bottles : [...bottles].sort(
			(a, b) =>
				a.producer.localeCompare(b.producer) ||
				a.cuvee.localeCompare(b.cuvee) ||
				b.vintage.localeCompare(a.vintage) ||
				a.location.localeCompare(b.location)
		)
	);
	// "H5 · Home": the place, and its storage group when it says more
	const where = (b: Bottle) =>
		[b.location, b.location_group !== b.location && b.location_group !== appSettings.other_group ? b.location_group : null].filter(Boolean).join(' · ');
</script>

{#if lines.length}
	<ul>
		{#each lines.slice(0, limit) as b (b.bottle_id)}
			<li class:current={b.bottle_id === current}>
				<!-- the bottles' pips, its label under them (a producer's page) -->
				<div class="side">
				<a class="ends" href={links.wineBottle(b.wine_id, b.bottle_id)} title="Open this bottle" tabindex="-1" aria-hidden="true">
					{#each { length: Math.min(b.qty, 12) }}
						<BottleEnd
							region={regionColors[b.region] ?? FALLBACK_REGION}
							color={b.color}
							format={b.format}
							size={11}
							title="{regionLabel(b.region)} · {b.color ?? ''}{b.format ? ` · ${b.format}` : ''}"
						/>
					{/each}
				</a>
				{#if labels[b.wine_id] && appSettings.wine_labels !== 'off'}
					{@const l = labels[b.wine_id]}
					<span class="thumb"><LabelThumbs labels={[{ url: l.url, vintages: [l.from_vintage ?? b.vintage] }]} name={b.cuvee || b.producer} align="left" /></span>
				{/if}
				</div>
				<div class="label">
					<a href={links.wineBottle(b.wine_id, b.bottle_id)}><b>{b.producer}</b>{b.cuvee ? ` – ${b.cuvee}` : ''}</a>
					<span class="vintage num">{b.vintage}</span><CriticPills scores={b.scores} />
					{#if b.bottle_id === current}<span class="this">this bottle</span>{/if}
					{#if b.maturity}<span class="mat"><MaturityBadge maturity={b.maturity} from={b.drink_from} to={b.drink_to} /></span>{/if}
					{#if b.appellation}<div class="under muted">{b.appellation}</div>{/if}
				</div>
				<div class="where muted">
					{#if prices}
						<span class="num">{#if paid(b)}<b class="paid" title="Paid a bottle">{paid(b)}</b>{' · '}{/if}{b.qty} {b.qty === 1 ? 'bottle' : 'bottles'}</span>
						<span>{[b.purchase_date && fmtDate(b.purchase_date), b.vendor].filter(Boolean).join(' · ')}</span>
					{:else}
						<span class="num">{b.qty} {b.qty === 1 ? 'bottle' : 'bottles'}</span>
						<span>{where(b)}</span>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
	{#if lines.length > limit}
		<button class="btn more" onclick={() => (limit += PAGE)}>Show more ({lines.length - limit} lines)</button>
	{/if}
{:else}
	<p class="muted">{empty}</p>
{/if}

<style>
	ul {
		list-style: none;
		margin: -6px 0;
		padding: 0;
	}
	li {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 8px 0;
		font-size: 13px;
	}
	li + li {
		border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	/* the bottle whose page this is */
	li.current {
		margin: 0 -8px;
		padding: 8px;
		border-radius: 6px;
		background: var(--accent-soft);
	}
	li.current + li {
		border-top-color: transparent;
	}
	.ends {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 2px;
		width: 80px; /* six to a row: the names line up */
	}
	/* the pips' column: a label under them, at its width */
	.side {
		display: flex;
		flex-direction: column;
		gap: 6px;
		flex: none;
		width: 80px;
		align-self: flex-start;
		padding-top: 3px;
	}
	.thumb {
		display: flex;
	}
	.side :global(button.thumb img) {
		max-width: 76px;
	}
	.label {
		flex: 1;
		min-width: 0;
	}
	.vintage {
		color: var(--muted);
		margin-left: 2px;
	}
	.under {
		font-size: 12px;
	}
	.this {
		margin-left: 6px;
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		white-space: nowrap;
	}
	.mat {
		margin-left: 6px;
	}
	.where {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		flex: none;
		max-width: 40%;
		font-size: 12px;
		text-align: right;
	}
	.paid {
		color: var(--text);
	}
	.more {
		margin-top: 12px;
	}
</style>
