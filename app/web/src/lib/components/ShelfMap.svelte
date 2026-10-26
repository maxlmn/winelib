<script lang="ts">
	import type { Bottle, Location, RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import { money } from '#lib/format.ts';
	import { groupOrder } from '#lib/settings.svelte.ts';

	interface Props {
		locations: Location[];
		/** whole cellar: drives fill vs capacity, so the map stays physically stable */
		all: Bottle[];
		/** bottles matching the page's non-location filters: drives the region bars */
		matching: Bottle[];
		selected: string[];
		regionColors: RegionColors;
		onselect: (loc: string) => void;
	}

	let { locations, all, matching, selected, regionColors, onselect }: Props = $props();

	const filtering = $derived(matching.length !== all.length);

	const tiles = $derived.by(() => {
		const held = new Map<string, { qty: number; value: number }>();
		for (const b of all) {
			const h = held.get(b.location) ?? { qty: 0, value: 0 };
			h.qty += b.qty;
			h.value += b.qty * b.market_base;
			held.set(b.location, h);
		}
		const mix = new Map<string, Map<string, number>>();
		const contents = new Map<string, Bottle[]>();
		for (const b of matching) {
			const m = mix.get(b.location) ?? new Map();
			m.set(b.region, (m.get(b.region) ?? 0) + b.qty);
			mix.set(b.location, m);
			contents.set(b.location, [...(contents.get(b.location) ?? []), b]);
		}
		return locations.map((l) => {
			const h = held.get(l.name) ?? { qty: 0, value: 0 };
			const regions = [...(mix.get(l.name) ?? [])].sort((a, b) => b[1] - a[1]);
			const nMatch = regions.reduce((n, [, c]) => n + c, 0);
			// Bars are scaled to capacity, so the grey remainder is free space
			const scale = l.capacity ? Math.max(l.capacity, h.qty) : h.qty || 1;
			return { ...l, qty: h.qty, value: h.value, regions, nMatch, scale, contents: contents.get(l.name) ?? [] };
		});
	});

	const groups = $derived(
		groupOrder().map((name) => {
			const g = tiles.filter((t) => t.group === name);
			const free = g.reduce((n, t) => n + (t.capacity ? Math.max(t.capacity - t.qty, 0) : 0), 0);
			return {
				name,
				tiles: g,
				qty: g.reduce((n, t) => n + t.qty, 0),
				value: g.reduce((n, t) => n + t.value, 0),
				free: g.some((t) => t.capacity) ? free : null
			};
		}).filter((g) => g.tiles.length)
	);

	const regionColor = (r: string) => regionColors[r] ?? FALLBACK_REGION;
</script>

<div class="legend muted">
	Bars show region mix against capacity (grey = free slots). Click a bin to filter by it; click again to clear.
	{#if filtering}Bins with nothing matching the current filters are dimmed.{/if}
</div>

{#each groups as g (g.name)}
	<section>
		<header>
			<h3>{g.name}</h3>
			<span class="muted num">{g.qty} btl{g.value ? ` · ${money(g.value)}` : ''}{g.free !== null ? ` · ${g.free} free` : ''}</span>
		</header>
		<div class="grid">
			{#each g.tiles as t (t.name)}
				{@const over = t.capacity !== null && t.qty > t.capacity}
				<button
					class="tile"
					class:selected={selected.includes(t.name)}
					class:dim={filtering && !t.nMatch}
					onclick={() => onselect(t.name)}
				>
					<div class="top">
						<span class="name">{t.name}</span>
						<span class="stat num" class:over>
							{#if filtering}{t.nMatch || '—'}{:else if t.capacity}{t.qty}/{t.capacity}{:else}{t.qty}{/if}
						</span>
					</div>
					<div class="bar">
						{#each t.regions as [region, n]}
							<span style:width="{(n / t.scale) * 100}%" style:background={regionColor(region)}></span>
						{/each}
					</div>
					{#if t.contents.length}
						<div class="pop card">
							<div class="pop-head">
								<b>{t.name}</b>
								<span class="muted num">{t.qty} btl{t.capacity ? ` / ${t.capacity}` : ''}{t.value ? ` · ${money(t.value)}` : ''}</span>
							</div>
							{#each t.contents.slice(0, 8) as b (b.bottle_id)}
								<div class="pop-row">
									<span class="dot" style:background={typeColor(b.color)}></span>
									<span class="ellipsis">{b.producer}{b.cuvee ? ` · ${b.cuvee}` : ''}</span>
									<span class="muted num">{b.vintage}{b.qty > 1 ? ` ×${b.qty}` : ''}</span>
								</div>
							{/each}
							{#if t.contents.length > 8}<div class="muted">+{t.contents.length - 8} more</div>{/if}
						</div>
					{/if}
				</button>
			{/each}
		</div>
	</section>
{/each}

<style>
	.legend {
		font-size: 12px;
		margin-bottom: 14px;
	}
	section + section {
		margin-top: 20px;
	}
	header {
		display: flex;
		align-items: baseline;
		gap: 10px;
		margin-bottom: 8px;
	}
	h3 {
		margin: 0;
		font-size: 14px;
	}
	header span {
		font-size: 12px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(108px, 1fr));
		gap: 8px;
	}
	.tile {
		position: relative;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		gap: 10px;
		min-height: 64px;
		padding: 8px 9px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
		cursor: pointer;
		text-align: left;
		transition: transform 0.12s, border-color 0.12s, opacity 0.12s;
	}
	.tile:hover {
		border-color: var(--accent);
		transform: translateY(-1px);
		z-index: 5;
	}
	.tile.selected {
		border-color: var(--gold);
		box-shadow: 0 0 0 2px var(--gold);
	}
	.tile.dim {
		opacity: 0.35;
	}
	.top {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 4px;
	}
	.name {
		font-weight: 650;
	}
	.stat {
		font-size: 12px;
		color: var(--muted);
	}
	.stat.over {
		color: var(--down);
		font-weight: 600;
	}
	.bar {
		display: flex;
		height: 7px;
		border-radius: 4px;
		overflow: hidden;
		background: color-mix(in srgb, var(--muted) 18%, transparent);
	}
	.bar span {
		height: 100%;
	}
	.bar span + span {
		box-shadow: inset 1px 0 0 var(--surface-2);
	}
	.pop {
		display: none;
		position: absolute;
		left: 50%;
		top: calc(100% + 6px);
		transform: translateX(-50%);
		width: 300px;
		padding: 10px 12px;
		font-size: 12px;
		pointer-events: none;
		z-index: 30;
	}
	.tile:hover .pop {
		display: block;
	}
	.pop-head {
		display: flex;
		justify-content: space-between;
		margin-bottom: 6px;
	}
	.pop-row {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 2px 0;
	}
	.ellipsis {
		flex: 1;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}
</style>
