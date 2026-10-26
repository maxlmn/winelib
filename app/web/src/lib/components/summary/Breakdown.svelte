<script lang="ts">
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Breakdown } from '#lib/api/summary.ts';
	import { FALLBACK_REGION, TYPE_COLORS } from '#lib/colors.ts';
	import { links } from '#lib/links.ts';
	import BarList from './BarList.svelte';
	import ColumnChart from './ColumnChart.svelte';
	import PaletteBand from './PaletteBand.svelte';

	interface Props {
		data: Breakdown;
		/** "tastings" or "bottles" */
		unit: string;
		/** optional link for a color / region / vintage, e.g. the filtered cellar */
		filterHref?: (key: 'color' | 'region' | 'vintage', value: string) => string | undefined;
	}

	let { data, unit, filterHref }: Props = $props();

	const colors = $derived(
		data.colors.map((c) => ({ label: c.name, count: c.count, color: TYPE_COLORS[c.name], href: filterHref?.('color', c.name) }))
	);
	const regions = $derived(
		data.regions.map((r) => ({ key: r.name, label: regionLabel(r.name), count: r.count, color: r.color, href: links.region(r.name) }))
	);
	const producers = $derived(
		data.producers.map((p) => ({ key: p.id, label: p.name, count: p.count, color: p.color, href: links.producer(p.id) }))
	);
	const appellations = $derived(
		data.appellations.map((a) => ({ key: a.id, label: a.name, count: a.count, color: a.color, href: links.appellation(a.id) }))
	);
	// Bars in the grape's usual wine color (red, white, sparkling...)
	const grapes = $derived(
		data.grapes.map((g) => ({
			key: g.name ?? '…other',
			label: g.name ?? `${g.grapes} other grapes`,
			count: g.count,
			color: (g.type && TYPE_COLORS[g.type]) || FALLBACK_REGION,
			href: g.name ? links.grape(g.name) : undefined
		}))
	);
	// Each vintage stacked by region, in the regions' colors
	const vintages = $derived(
		data.vintages.map((v) => ({
			label: v.name,
			count: v.count,
			href: filterHref?.('vintage', v.name),
			segments: v.regions.map((r) => ({ label: regionLabel(r.name), count: r.count, color: r.color }))
		}))
	);
</script>

<!-- The whole at a glance: a band by region, a thinner one by color -->
<section class="card palette">
	<PaletteBand segments={regions.map((r) => ({ label: r.label, count: r.count, color: r.color, href: r.href }))} {unit} height={26} />
	<PaletteBand segments={colors} {unit} height={8} />
	<div class="legend">
		{#each colors as c (c.label)}
			<svelte:element this={c.href ? 'a' : 'span'} href={c.href} class="key">
				<span class="dot" style:background={c.color}></span>{c.label} <span class="muted num">{c.count}</span>
			</svelte:element>
		{/each}
	</div>
</section>

<div class="grid">
	<section class="card">
		<h2>Regions</h2>
		<BarList bars={regions} total={data.total} {unit} pill />
	</section>
	<section class="card">
		<h2>Producers</h2>
		<BarList bars={producers} total={data.total} {unit} />
	</section>
	<section class="card">
		<h2>Appellations</h2>
		<BarList bars={appellations} total={data.total} {unit} />
	</section>
	<section class="card">
		<h2>Grapes</h2>
		<BarList bars={grapes} total={data.total} {unit} />
	</section>
	<section class="card wide">
		<h2>By vintage</h2>
		<ColumnChart columns={vintages} {unit} height={140} />
	</section>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 14px;
		align-items: start;
	}
	.palette {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 14px 16px 12px;
		margin-bottom: 14px;
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 14px;
		margin-top: 8px;
		font-size: 12px;
	}
	.key {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		color: inherit;
	}
	.key .dot {
		width: 8px;
		height: 8px;
	}
	section {
		padding: 14px 16px 16px;
	}
	.wide {
		grid-column: 1 / -1;
	}
	h2 {
		font-size: 14px;
		margin: 0 0 12px;
	}
	@media (max-width: 900px) {
		.grid {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
