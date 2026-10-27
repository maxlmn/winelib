<script lang="ts">
	import RegionStrip from '#lib/components/RegionStrip.svelte';
	import { links } from '#lib/links.ts';
	import { barWidth } from '#lib/format.ts';
	import { fmtDay, wineName } from './journal.ts';
	import type { Tasting } from '#lib/api/tastings.ts';

	let { tastings, label = 'Every wine, oldest on the left: its region’s color, its own color below' }: { tastings: Tasting[]; label?: string } =
		$props();

	const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	const GAP = 2; // RegionStrip's gap between bars

	// Every wine tasted in one line, oldest on the left, as poured within a day: a bar each in its region's color,
	// its own color on the track below
	const sorted = $derived([...tastings].sort((a, b) => a.date.localeCompare(b.date) || (a.seq ?? 0) - (b.seq ?? 0)));
	const pips = $derived(
		sorted.map((t) => ({
			region: t.region,
			color: t.color,
			format: t.format,
			label: wineName(t),
			sub: `${fmtDay(t.date)} · ${t.location}`,
			href: links.tasting(t.id)
		}))
	);

	// Under the line: each year, and each month where there's room for it
	const marks = $derived.by(() => {
		const out: { x: number; text: string; year: boolean }[] = [];
		let x = 0;
		let last = '';
		let lastLabel = -Infinity;
		for (const t of sorted) {
			const month = t.date.slice(0, 7);
			if (month !== last) {
				const year = month.slice(0, 4) !== last.slice(0, 4);
				if (year || x - lastLabel >= 30) {
					out.push({ x, text: year ? month.slice(0, 4) : MONTHS[Number(month.slice(5)) - 1], year });
					lastLabel = x;
				}
				last = month;
			}
			x += 5 * Math.min(2, barWidth(t.format) / 4) + GAP; // a bar's width (RegionStrip's tracks)
		}
		return out;
	});

	// Opens on the latest wines: scroll left for older ones
	let scroller = $state<HTMLDivElement>();
	$effect(() => {
		void pips;
		if (scroller) scroller.scrollLeft = scroller.scrollWidth;
	});
</script>

{#if pips.length > 1}
	<div class="ribbon card">
		<div class="label">{label}</div>
		<div class="scroller" bind:this={scroller}>
			<div class="line">
				<RegionStrip {pips} height={18} />
				<div class="marks">
					{#each marks as m (m.x)}<span class="mark num" class:year={m.year} style:left="{m.x}px">{m.text}</span>{/each}
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.ribbon {
		padding: 12px 16px 8px;
		margin-bottom: 14px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
		margin-bottom: 8px;
	}
	.scroller {
		overflow-x: auto;
		padding-bottom: 6px;
	}
	.line {
		width: max-content;
		min-width: 100%;
	}
	.line :global(.strip) {
		flex-wrap: nowrap;
	}
	.marks {
		position: relative;
		height: 18px;
		margin-top: 4px;
		border-top: 1px solid var(--border);
	}
	.mark {
		position: absolute;
		top: 0;
		padding: 3px 0 0 3px;
		border-left: 1px solid var(--border);
		font-size: 11px;
		color: var(--muted);
		white-space: nowrap;
	}
	.mark.year {
		color: var(--text);
		font-weight: 600;
		border-left-color: var(--muted);
	}
</style>
