<script lang="ts">
	import CriticPills from '#lib/components/CriticPills.svelte';
	import { regionLabel } from '#lib/regions.svelte.ts';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';
	import RegionStrip from '#lib/components/RegionStrip.svelte';
	import BottleEnd from '#lib/components/BottleEnd.svelte';
	import type { Pip } from '#lib/components/RegionStrip.svelte';
	import { bottlePips } from '#lib/pips.ts';
	import type { Bottle, RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION, TYPE_COLORS, typeColor } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import { money, plural, symbol } from '#lib/format.ts';
	import { appSettings, groupOrder } from '#lib/settings.svelte.ts';
	import { colorSection } from '#lib/wineList.ts';

	let {
		bottles,
		regionColors,
		prices = false,
		plain = false,
		current = null,
		onwine,
		shown = null
	}: {
		bottles: Bottle[];
		regionColors: RegionColors;
		/** each line's price paid a bottle, in its currency, and where it was bought (the home page's recent purchases) */
		prices?: boolean;
		/** one wine's bottles (its page, a bottle's): no rack strip, no reds / whites split, its lines as they are */
		plain?: boolean;
		/** the bottle whose page this is: its line marked */
		current?: number | null;
		/** a bottle pointed at (its line or its pip hovered, its line tapped outside its links), e.g. for a map to show
		 * its wine */
		onwine?: (b: Bottle) => void;
		/** the bottle shown there: its line marked */
		shown?: number | null;
	} = $props();
	const paid = (b: Bottle) => (b.price ? `${symbol(b.currency ?? appSettings.currency)}${Math.round(b.price).toLocaleString()}` : null);

	// Each storage group (Settings) is one card; every other location gets its own
	const cardName = (b: Bottle) => (b.location_group === appSettings.other_group ? b.location : b.location_group);

	// A card's order, as a wine list's: by colour (sparkling first, sweet and fortified last), then region, then
	// appellation (none last), then producer, cuvée and vintage (the youngest first)
	const text = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: 'base' });
	const byListOrder = (a: Bottle, b: Bottle) =>
		colorSection(a.color).order - colorSection(b.color).order ||
		text(a.region, b.region) ||
		Number(!a.appellation) - Number(!b.appellation) ||
		text(a.appellation ?? '', b.appellation ?? '') ||
		text(a.producer, b.producer) ||
		text(a.cuvee, b.cuvee) ||
		b.vintage.localeCompare(a.vintage);
	// ...in sections by colour, each with its regions
	type Section = { title: string; color: string | null; qty: number; regions: { region: string; lines: Bottle[] }[] };
	const sectioned = (list: Bottle[]) => {
		const out: Section[] = [];
		for (const b of list) {
			const s = colorSection(b.color);
			let sec = out.at(-1);
			if (!sec || sec.title !== s.title) {
				sec = { title: s.title, color: b.color, qty: 0, regions: [] };
				out.push(sec);
			}
			sec.qty += b.qty;
			let reg = sec.regions.at(-1);
			if (!reg || reg.region !== b.region) {
				reg = { region: b.region, lines: [] };
				sec.regions.push(reg);
			}
			reg.lines.push(b);
		}
		return out;
	};

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
					sections: sectioned(sorted),
					// the rack in the list's order: a colour's bottles together, a region's within it
					strip: sorted
				};
			});
	});

	const regionColor = (r: string) => regionColors[r] ?? FALLBACK_REGION;

	// A card's strip: a pip per bottle; hovering one lights its line in the list (and points at its wine)
	let hot = $state<Pip['key'] | null>(null);
	const byId = $derived(new Map(bottles.map((b) => [b.bottle_id, b])));
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

{#snippet wineList(title: string | null, list: Bottle[], qty: number, color: string, sub = false)}
	{#if list.length}
		<div>
			{#if title && sub}<h5><span class="bar" style:background={color}></span>{title} <span class="muted num">{qty}</span></h5>
			{:else if title}<h4><span class="dot" style:background={color}></span>{title} <span class="muted num">{qty}</span></h4>{/if}
			<ul>
				{#each list as b (b.bottle_id)}
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
					<li
						class:hot={b.bottle_id === hot}
						class:current={b.bottle_id === current}
						class:points={!!onwine}
						class:shown={onwine && shown === b.bottle_id}
						onpointerenter={(e) => e.pointerType === 'mouse' && onwine?.(b)}
						onclick={(e) => !(e.target as HTMLElement).closest('a, button') && onwine?.(b)}
					>
						<a class="line-ends" href={links.bottle(b.bottle_id)} title="Open this bottle" tabindex="-1" aria-hidden="true">{@render ends(b)}</a>
						<span class="label">
							<a href={links.bottle(b.bottle_id)}>
								<b>{b.producer}</b>{b.cuvee ? ` – ${b.cuvee}` : ''}
							</a>
							{#if b.appellation}<span class="muted">({b.appellation})</span>{/if}
							<span class="meta num">[{b.vintage}]</span><CriticPills scores={b.scores} />
							{#if prices && paid(b)}<span class="paid num" title="Paid a bottle">{paid(b)}</span>{/if}
							{#if prices && b.vendor}<span class="vendor muted" title="Bought from">{b.vendor}</span>{/if}
								{#if b.bottle_id === current}<span class="this">this bottle</span>{/if}
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
				{#if !plain}
					<span class="split num">
						<span class="pair"><span class="dot" style:background={TYPE_COLORS.Red}></span>{c.redQty}</span>
						<span class="pair"><span class="dot" style:background={TYPE_COLORS.White}></span>{c.otherQty}</span>
					</span>
				{/if}
			</div>
			{#if !plain}
				<RegionStrip
					pips={bottlePips(c.strip)}
					variant="rack"
					height={11}
					active={onwine ? shown : null}
					onhover={(k) => {
						hot = k;
						const b = k == null ? null : byId.get(Number(k));
						if (b) onwine?.(b);
					}}
				/>
			{/if}
		</summary>
		{#if plain}
			<div class="columns">{@render wineList(null, [...c.reds, ...c.others], c.qty, '')}</div>
		{:else}
			<!-- by colour, then region, then appellation: one column, a colour's heading over its regions -->
			<div class="sections">
				{#each c.sections as s (s.title)}
					<h4><span class="dot" style:background={typeColor(s.color ?? '')}></span>{s.title} <span class="muted num">{s.qty}</span></h4>
					{#each s.regions as r (r.region)}
						{@render wineList(regionLabel(r.region), r.lines, r.lines.reduce((n, b) => n + b.qty, 0), regionColor(r.region), true)}
					{/each}
				{/each}
			</div>
		{/if}
	</details>
{/each}

<style>
	.card-box {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		margin-bottom: 10px;
		overflow: hidden;
		background: var(--surface);
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
	.sections {
		padding: 14px 16px 6px;
	}
	.sections h4 {
		margin-top: 6px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
	}
	/* a region under its colour: its name small, its colour's bar */
	h5 {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 8px 0 4px;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--muted);
	}
	h5 .bar {
		width: 3px;
		height: 11px;
		border-radius: 1px;
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
	/* the bottle whose page this is */
	li.current {
		background: var(--accent-soft);
		box-shadow: inset 2px 0 0 var(--accent);
		border-radius: 4px;
		padding-left: 6px;
	}
	.this {
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		white-space: nowrap;
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
	.vendor {
		margin-left: 6px;
		font-size: 12px;
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
	/* a line that shows its wine on a map when pointed at (the Cellar page's); the one shown on a soft tint */
	li.points {
		margin-inline: -6px;
		padding-inline: 6px;
		cursor: pointer;
	}
	li.points:hover {
		background: color-mix(in srgb, var(--accent) 5%, transparent);
	}
	li.shown,
	li.shown:hover {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}
</style>
