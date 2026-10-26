<script lang="ts">
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Place, Tasting, Visit } from '#lib/api/tastings.ts';
	import type { RegionColors } from '#lib/types.ts';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import { plural } from '#lib/format.ts';

	interface Props {
		tastings: Tasting[];
		visits: Visit[];
		places: Record<string, Place>;
		regionColors: RegionColors;
		/** regions currently filtered on; clicking a legend entry toggles one */
		selectedRegions: string[];
		onregion: (regions: string[]) => void;
	}

	let { tastings, visits, places, regionColors, selectedRegions, onregion }: Props = $props();

	const M = { left: 34, right: 8, top: 10, bottom: 24 };
	const AREA_H = 260;
	const STARS_H = 150;
	const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

	let width = $state(800);
	let hover = $state<number | null>(null);

	const monthIndex = (iso: string) => +iso.slice(0, 4) * 12 + +iso.slice(5, 7) - 1;
	const monthLabel = (i: number, short = false) => `${MONTHS[i % 12]} ${short ? `’${String(Math.floor(i / 12)).slice(2)}` : Math.floor(i / 12)}`;

	const data = $derived.by(() => {
		const dates = [...tastings.map((t) => t.date), ...visits.map((v) => v.date)];
		if (!dates.length) return null;
		const first = Math.min(...dates.map(monthIndex));
		const n = Math.max(...dates.map(monthIndex)) - first + 1;
		const months = Array.from({ length: n }, () => ({ total: 0, stars: 0, regions: new Map<string, number>() }));
		const regionTotals = new Map<string, number>();
		for (const t of tastings) {
			const m = months[monthIndex(t.date) - first];
			m.total += 1;
			m.regions.set(t.region, (m.regions.get(t.region) ?? 0) + 1);
			regionTotals.set(t.region, (regionTotals.get(t.region) ?? 0) + 1);
		}
		// Stars are per occasion (day + place), not per wine
		const occasions = new Map<string, number>();
		for (const x of [...tastings, ...visits]) if (x.place_id) occasions.set(`${x.date}|${x.place_id}`, places[x.place_id]?.stars ?? 0);
		for (const [key, s] of occasions) months[monthIndex(key.slice(0, 10)) - first].stars += s;
		// Biggest regions at the bottom of the stack
		const regions = [...regionTotals].sort((a, b) => b[1] - a[1]).map(([r]) => r);
		return { first, months, regions, regionTotals };
	});

	function niceTicks(max: number, count = 4) {
		if (max <= 0) return [0];
		const raw = max / count;
		const mag = 10 ** Math.floor(Math.log10(raw));
		const step = [1, 2, 5, 10].map((s) => s * mag).find((s) => s >= raw)!;
		return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step);
	}

	const n = $derived(data?.months.length ?? 0);
	const band = $derived((width - M.left - M.right) / Math.max(n, 1));
	const x = (i: number) => M.left + i * band;
	const gap = $derived(band > 6 ? 1 : 0);

	const areaTicks = $derived(niceTicks(Math.max(1, ...(data?.months.map((m) => m.total) ?? [1]))));
	const starTicks = $derived(niceTicks(Math.max(1, ...(data?.months.map((m) => m.stars) ?? [1])), 3));
	const hasStars = $derived(!!data?.months.some((m) => m.stars));

	// January labels for long spans; every month (or every few) for short ones
	const labels = $derived.by(() => {
		if (!data) return [];
		const all = data.months.map((_, i) => i + data.first);
		// The first (partial) year gets a label only when there's room before the next January
		if (n > 24) return all.filter((i) => i % 12 === 0 || (i === data.first && i % 12 < 6)).map((i) => ({ i, text: String(Math.floor(i / 12)) }));
		const every = Math.ceil(n / Math.max(1, Math.floor((width - M.left) / 56)));
		return all.filter((_, k) => k % every === 0).map((i) => ({ i, text: monthLabel(i, true) }));
	});

	function onmove(e: PointerEvent) {
		const r = (e.currentTarget as SVGElement).getBoundingClientRect();
		const i = Math.floor((e.clientX - r.left - M.left) / band);
		hover = i >= 0 && i < n ? i : null;
	}

	const regionColor = (r: string) => regionColors[r] ?? FALLBACK_REGION;
	const toggleRegion = (r: string) =>
		onregion(selectedRegions.includes(r) ? selectedRegions.filter((x) => x !== r) : [...selectedRegions, r]);
</script>

{#snippet axes(h: number, ticks: number[], y: (v: number) => number)}
	{#each ticks as t}
		<line class="grid" x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} />
		<text class="tick" x={M.left - 6} y={y(t)} text-anchor="end" dominant-baseline="middle">{t}</text>
	{/each}
	{#each labels as l}
		<text class="tick" x={x(l.i - data!.first) + band / 2} y={h - 6} text-anchor="middle">{l.text}</text>
	{/each}
{/snippet}

{#snippet guide(h: number)}
	{#if hover !== null}<rect class="hover" x={x(hover)} y={M.top} width={band} height={h - M.top - M.bottom} />{/if}
{/snippet}

<p class="muted caption">Reflects the active filters and period. Pick <b>All time</b> for the full history.</p>

{#if !data}
	<p class="muted">Nothing to chart.</p>
{:else}
	{@const yA = (v: number) => AREA_H - M.bottom - (v / areaTicks.at(-1)!) * (AREA_H - M.top - M.bottom)}
	{@const yS = (v: number) => STARS_H - M.bottom - (v / starTicks.at(-1)!) * (STARS_H - M.top - M.bottom)}
	<div class="chart" bind:clientWidth={width}>
		<h3>Tastings over time</h3>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<svg {width} height={AREA_H} onpointermove={onmove} onpointerleave={() => (hover = null)}>
			{@render guide(AREA_H)}
			{@render axes(AREA_H, areaTicks, yA)}
			{#each data.months as m, i}
				{#if m.total}
					{@const stack = data.regions.filter((r) => m.regions.has(r))}
					{#each stack as r, k}
						{@const below = stack.slice(0, k).reduce((s, q) => s + m.regions.get(q)!, 0)}
						{@const v = m.regions.get(r)!}
						<rect
							x={x(i) + gap / 2}
							y={yA(below + v)}
							width={Math.max(band - gap, 0.5)}
							height={yA(below) - yA(below + v)}
							fill={regionColor(r)}
							opacity={hover === null || hover === i ? 1 : 0.55}
						/>
					{/each}
				{/if}
			{/each}
		</svg>
		{#if hover !== null}
			{@const m = data.months[hover]}
			<!-- in the half of the chart away from the hovered month -->
			<div class="tip card" style:left="{x(hover) > width / 2 ? M.left + 10 : width - M.right - 220}px">
				<b>{monthLabel(hover + data.first)}</b>
				<div class="muted num">{plural(m.total, 'wine')}{m.stars ? ` · ${m.stars} ★` : ''}</div>
				{#each [...m.regions].sort((a, b) => b[1] - a[1]).slice(0, 8) as [r, c]}
					<div class="tip-row"><span class="swatch" style:background={regionColor(r)}></span>{regionLabel(r)}<span class="num">{c}</span></div>
				{/each}
			</div>
		{/if}
		<div class="legend">
			{#each data.regions as r}
				<button class="key" class:on={selectedRegions.includes(r)} onclick={() => toggleRegion(r)} title="Filter on {regionLabel(r)}">
					<span class="swatch" style:background={regionColor(r)}></span>{regionLabel(r)}
					<span class="muted num">{data.regionTotals.get(r)}</span>
				</button>
			{/each}
		</div>

		<h3>Michelin stars over time</h3>
		{#if hasStars}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<svg {width} height={STARS_H} onpointermove={onmove} onpointerleave={() => (hover = null)}>
				{@render guide(STARS_H)}
				{@render axes(STARS_H, starTicks, yS)}
				{#each data.months as m, i}
					{#if m.stars}
						<rect class="star" x={x(i) + gap / 2} y={yS(m.stars)} width={Math.max(band - gap, 0.5)} height={yS(0) - yS(m.stars)} />
					{/if}
				{/each}
			</svg>
		{:else}
			<p class="muted">No Michelin-starred visits in the current selection.</p>
		{/if}
	</div>
{/if}

<style>
	.caption {
		margin: 0 0 6px;
		font-size: 12px;
	}
	.chart {
		position: relative;
	}
	h3 {
		font-size: 14px;
		margin: 14px 0 6px;
	}
	svg {
		display: block;
		overflow: visible;
		touch-action: pan-y;
	}
	.grid {
		stroke: var(--border);
		stroke-width: 1;
	}
	.tick {
		fill: var(--muted);
		font-size: 11px;
		font-variant-numeric: tabular-nums;
	}
	.hover {
		fill: var(--accent-soft);
	}
	.star {
		fill: var(--gold);
	}
	.tip {
		position: absolute;
		top: 40px;
		width: 210px;
		padding: 8px 10px;
		font-size: 12px;
		pointer-events: none;
		z-index: 2;
	}
	.tip-row {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 6px;
	}
	.swatch {
		display: inline-block;
		width: 4px;
		height: 12px;
		border-radius: 2px;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 6px;
		margin: 10px 0 4px;
	}
	.key {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 2px 8px;
		border: 1px solid transparent;
		border-radius: 12px;
		background: none;
		font-size: 12px;
		cursor: pointer;
	}
	.key:hover {
		border-color: var(--border);
	}
	.key.on {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
</style>
