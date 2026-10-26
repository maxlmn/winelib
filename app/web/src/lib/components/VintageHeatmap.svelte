<script lang="ts">
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Bottle, RegionColors } from '#lib/types.ts';
	import { links } from '#lib/links.ts';
	import { FALLBACK_REGION, ramp } from '#lib/colors.ts';
	import { compact, money } from '#lib/format.ts';

	interface Props {
		bottles: Bottle[];
		regionColors: RegionColors;
		/** vintages: every exact vintage in the cell, e.g. all "NV - …" disgorgements under NV */
		onpick: (region: string, vintages: string[]) => void;
	}

	let { bottles, regionColors, onpick }: Props = $props();

	let metric = $state<'qty' | 'value'>('qty');

	// "NV - Oct 2024" groups with NV
	const base = (v: string) => v.split(' - ')[0];

	const grid = $derived.by(() => {
		const cells = new Map<string, { qty: number; value: number; vintages: Set<string> }>();
		const regionTotals = new Map<string, number>();
		const vintages = new Set<string>();
		for (const b of bottles) {
			const v = base(b.vintage);
			vintages.add(v);
			const key = `${b.region}|${v}`;
			const c = cells.get(key) ?? { qty: 0, value: 0, vintages: new Set() };
			c.qty += b.qty;
			c.value += b.qty * b.market_base;
			c.vintages.add(b.vintage);
			cells.set(key, c);
			regionTotals.set(b.region, (regionTotals.get(b.region) ?? 0) + (metric === 'qty' ? b.qty : b.qty * b.market_base));
		}
		const cols = [...vintages].sort((a, b) => {
			const x = /^\d+$/.test(a), y = /^\d+$/.test(b);
			return x && y ? +a - +b : x ? -1 : y ? 1 : a.localeCompare(b);
		});
		const rows = [...regionTotals].sort((a, b) => b[1] - a[1]).map(([r]) => r);
		const peak = Math.max(1, ...[...cells.values()].map((c) => c[metric]));
		return { cells, cols, rows, peak };
	});
</script>

<div class="controls">
	<span class="muted">Shade by</span>
	<div class="seg">
		<button class:on={metric === 'qty'} onclick={() => (metric = 'qty')}>Bottles</button>
		<button class:on={metric === 'value'} onclick={() => (metric = 'value')}>Value</button>
	</div>
	<span class="muted hint">Click a cell to filter by that region and vintage.</span>
</div>

<div class="scroll">
	<div class="hm" style:grid-template-columns="minmax(110px, max-content) repeat({grid.cols.length}, minmax(34px, 1fr))">
		<div></div>
		{#each grid.cols as v}<div class="vh num">{v}</div>{/each}
		{#each grid.rows as r (r)}
			<a class="rh" href={links.region(r)}><span class="swatch" style:background={regionColors[r] ?? FALLBACK_REGION}></span>{regionLabel(r)}</a>
			{#each grid.cols as v}
				{@const c = grid.cells.get(`${r}|${v}`)}
				{#if c}
					{@const s = ramp(regionColors[r] ?? FALLBACK_REGION, Math.sqrt(c[metric] / grid.peak))}
					<button
						class="cell num"
						style:background={s.fill}
						style:color={s.dark ? '#222' : '#fff'}
						title="{regionLabel(r)} {v} · {c.qty} btl · {money(c.value)}"
						onclick={() => onpick(r, [...c.vintages])}
					>
						{metric === 'qty' ? c.qty : compact(c.value)}
					</button>
				{:else}
					<div class="cell empty"></div>
				{/if}
			{/each}
		{/each}
	</div>
</div>

<style>
	.controls {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 14px;
		font-size: 13px;
	}
	.hint {
		font-size: 12px;
	}
	.seg button {
		padding: 4px 12px;
	}
	.scroll {
		overflow-x: auto;
	}
	.hm {
		display: grid;
		gap: 3px;
		font-size: 11px;
	}
	.vh {
		writing-mode: vertical-rl;
		transform: rotate(180deg);
		justify-self: center;
		color: var(--muted);
		padding-bottom: 4px;
	}
	.rh {
		font-weight: 600;
		font-size: 12px;
		align-self: center;
		padding-right: 8px;
		white-space: nowrap;
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.swatch {
		width: 4px;
		height: 14px;
		border-radius: 2px;
	}
	.cell {
		height: 28px;
		border: none;
		border-radius: 4px;
		font-size: 11px;
		cursor: pointer;
		transition: transform 0.1s;
	}
	.cell:hover {
		transform: scale(1.12);
		box-shadow: var(--shadow);
		position: relative;
		z-index: 2;
	}
	.cell.empty {
		background: color-mix(in srgb, var(--muted) 7%, transparent);
		cursor: default;
	}
	a.rh {
		color: inherit;
		text-decoration: none;
	}
	a.rh:hover {
		color: var(--accent);
	}
</style>
