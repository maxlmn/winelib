<script lang="ts">
	import type { Bottle } from '#lib/types.ts';
	import Change from '#lib/components/Change.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { amount, pct as change } from '#lib/format.ts';
	import { links } from '#lib/links.ts';

	/** Bottles with both a purchase price and a market quote: biggest gains and losses, in the bottle's own currency. */
	let { bottles, limit = 20 }: { bottles: Bottle[]; limit?: number } = $props();

	const priced = $derived(
		bottles
			.filter((b) => b.price && b.price > 0 && b.last_price && b.last_price > 0)
			.map((b) => ({ b, pct: change(b.price!, b.last_price!) }))
	);
	const gains = $derived(priced.filter((x) => x.pct >= 0).sort((x, y) => y.pct - x.pct).slice(0, limit));
	const losses = $derived(priced.filter((x) => x.pct < 0).sort((x, y) => x.pct - y.pct).slice(0, limit));
</script>

{#snippet column(title: string, rows: typeof gains, up: boolean)}
	<section>
		<h3 class:up class:down={!up}>{up ? '▲' : '▼'} {title}</h3>
		{#each rows as { b, pct } (b.bottle_id)}
			<div class="row">
				<span class="end"><BottleEnd region={regionColor(b.region)} color={b.color} format={b.format} size={11} title="{regionLabel(b.region)} · {b.color ?? ''}" /></span>
				<a class="wine" href={links.bottle(b.bottle_id)}>
					<b>{b.producer}</b>{b.cuvee ? ` – ${b.cuvee}` : ''} <span class="num muted">{b.vintage}</span>
				</a>
				<span class="num prices">{amount(b.price, b.currency)} → {amount(b.last_price)}</span>
				<span class="num pct"><Change value={pct} /></span>
				{#if b.lwin}
					<a class="quote" href={links.winelabs(b.lwin, b.vintage)} target="_blank" rel="noreferrer" title="Market quote on winelabs">↗</a>
				{:else}<span></span>{/if}
			</div>
		{:else}
			<p class="muted">No {up ? 'gains' : 'losses'}.</p>
		{/each}
	</section>
{/snippet}

{#if priced.length}
	<p class="muted note">{priced.length} lines with a market quote. Prices are per bottle, in the currency paid.</p>
	<div class="cols">
		{@render column('Highest gains', gains, true)}
		{@render column('Biggest losses', losses, false)}
	</div>
{:else}
	<p class="muted">No bottles with both a purchase price and a market price.</p>
{/if}

<style>
	.note {
		margin: 0 0 12px;
		font-size: 12px;
	}
	.cols {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
		gap: 24px;
	}
	h3 {
		font-size: 14px;
		margin: 0 0 8px;
	}
	.row {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto 5em 1em;
		align-items: baseline;
		gap: 10px;
		padding: 6px 2px;
		border-bottom: 1px solid var(--border);
		font-size: 13px;
	}
	.end {
		display: flex;
		align-self: center;
	}
	.wine {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.prices {
		color: var(--muted);
		font-size: 12px;
	}
	.pct {
		text-align: right;
		font-weight: 600;
		white-space: nowrap;
	}
	.up {
		color: var(--up);
	}
	.down {
		color: var(--down);
	}
	.quote {
		color: var(--muted);
		text-decoration: none;
	}
</style>
