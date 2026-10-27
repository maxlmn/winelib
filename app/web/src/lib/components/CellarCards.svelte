<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import RegionStrip from '#lib/components/RegionStrip.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import type { Pip } from '#lib/components/RegionStrip.svelte';
	import { bottlePips } from '#lib/pips.ts';
	import type { Bottle, RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION, TYPE_COLORS } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { money, plural, symbol } from '#lib/format.ts';
	import { appSettings, groupOrder } from '#lib/settings.svelte.ts';

	let {
		bottles,
		regionColors,
		prices = false
	}: {
		bottles: Bottle[];
		regionColors: RegionColors;
		/** each line's price paid a bottle, in its currency (the home page's recent purchases) */
		prices?: boolean;
	} = $props();
	const paid = (b: Bottle) => (b.price ? `${symbol(b.currency ?? appSettings.currency)}${Math.round(b.price).toLocaleString()}` : null);

	// Each storage group (Settings) is one card; every other location gets its own
	const cardName = (b: Bottle) => (b.location_group === appSettings.other_group ? b.location : b.location_group);

	const byListOrder = (a: Bottle, b: Bottle) =>
		a.region.localeCompare(b.region) ||
		a.producer.localeCompare(b.producer) ||
		a.cuvee.localeCompare(b.cuvee) ||
		b.vintage.localeCompare(a.vintage);

	const cards = $derived.by(() => {
		const groups = new Map<string, Bottle[]>();
		for (const b of bottles) groups.set(cardName(b), [...(groups.get(cardName(b)) ?? []), b]);
		return [...groups]
			.sort(([a], [b]) => {
				const order = groupOrder().slice(0, -1);
				const [x, y] = [order.indexOf(a), order.indexOf(b)];
				return (x < 0 ? 99 : x) - (y < 0 ? 99 : y) || a.localeCompare(b);
			})
			.map(([name, list]) => {
				const sorted = [...list].sort(byListOrder);
				const reds = sorted.filter((b) => b.color === 'Red');
				const others = sorted.filter((b) => b.color !== 'Red');
				return {
					name,
					qty: list.reduce((n, b) => n + b.qty, 0),
					value: list.reduce((n, b) => n + b.qty * b.market_base, 0),
					reds,
					others,
					redQty: reds.reduce((n, b) => n + b.qty, 0),
					otherQty: others.reduce((n, b) => n + b.qty, 0),
					strip: [...list].sort((a, b) => a.region.localeCompare(b.region))
				};
			});
	});

	const regionColor = (r: string) => regionColors[r] ?? FALLBACK_REGION;

	// A card's strip: a pip per bottle; hovering one lights its line in the list
	let hot = $state<Pip['key'] | null>(null);
</script>

{#snippet ends(b: Bottle)}
	{#each { length: b.qty }}
		<BottleEnd
			region={regionColor(b.region)}
			color={b.color}
			format={b.format}
			size={11}
			title="{regionLabel(b.region)} · {b.color ?? ''}{b.format ? ` · ${b.format}` : ''}"
		/>
	{/each}
{/snippet}

{#snippet wineList(title: string, list: Bottle[], qty: number, color: string)}
	{#if list.length}
		<div>
			<h4><span class="dot" style:background={color}></span>{title} <span class="muted num">{qty}</span></h4>
			<ul>
				{#each list as b (b.bottle_id)}
					<li class:hot={b.bottle_id === hot}>
						<span class="line-ends">{@render ends(b)}</span>
						<span class="label">
							<a href={links.bottle(b.bottle_id)}>
								<b>{b.producer}</b>{b.cuvee ? ` – ${b.cuvee}` : ''}
							</a>
							{#if b.appellation}<span class="muted">({b.appellation})</span>{/if}
							<span class="meta num">[{b.vintage}]</span><CriticPills scores={b.scores} />
							{#if prices && paid(b)}<span class="paid num" title="Paid a bottle">{paid(b)}</span>{/if}
								{#if b.maturity}<span class="mat"><MaturityBadge maturity={b.maturity} from={b.drink_from} to={b.drink_to} /></span>{/if}
						</span>
					</li>
				{/each}
			</ul>
		</div>
	{/if}
{/snippet}

{#each cards as c (c.name)}
	<details class="card-box" open={c === cards[0]}>
		<summary>
			<div class="sum-top">
				<b>{c.name}</b>
				<span class="muted num">{plural(c.qty, 'bottle')}{c.value ? ` · ${money(c.value)}` : ''}</span>
				<span class="split num">
					<span class="pair"><span class="dot" style:background={TYPE_COLORS.Red}></span>{c.redQty}</span>
					<span class="pair"><span class="dot" style:background={TYPE_COLORS.White}></span>{c.otherQty}</span>
				</span>
			</div>
			<RegionStrip pips={bottlePips(c.strip)} variant="rack" height={11} onhover={(k) => (hot = k)} />
		</summary>
		<div class="columns">
			{@render wineList('Reds', c.reds, c.redQty, TYPE_COLORS.Red)}
			{@render wineList('Whites & others', c.others, c.otherQty, TYPE_COLORS.White)}
		</div>
	</details>
{/each}

<style>
	.card-box {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		margin-bottom: 10px;
		overflow: hidden;
	}
	summary {
		list-style: none;
		cursor: pointer;
		padding: 12px 14px;
		background: var(--surface-2);
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	summary::-webkit-details-marker {
		display: none;
	}
	summary:hover {
		background: color-mix(in srgb, var(--accent) 8%, var(--surface-2));
	}
	.sum-top {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.split {
		margin-left: auto;
		display: inline-flex;
		gap: 14px;
	}
	.pair {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.columns {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
		gap: 24px;
		padding: 14px 16px 6px;
	}
	h4 {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 0 0 8px;
		font-size: 13px;
	}
	ul {
		list-style: none;
		padding: 0;
		margin: 0 0 10px;
	}
	li {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 3px 0;
		font-size: 13px;
		border-radius: 4px;
		transition: background 0.1s;
	}
	li.hot {
		background: var(--accent-soft);
	}
	.line-ends {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		flex: none;
		min-width: 18px;
		align-self: center;
	}
	.label {
		min-width: 0;
	}
	.paid {
		margin-left: 6px;
		font-size: 12px;
		font-weight: 600;
	}
	.meta {
		color: var(--muted);
		font-size: 12px;
	}
	.mat {
		margin-left: 6px;
	}
</style>
