<script lang="ts">
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';

	/** A list's progress as bottle ends, one per entry: filled in its region's colour once tasted (the wine's colour as
	 * the cork), a ring until then; a ring with a cork dot when owned but not yet tasted. Hovering one names the entry,
	 * as the cellar's racks do. */
	import type { Dot } from '#lib/api/lists.ts';

	let { dots, size = 14 }: { dots: Dot[]; size?: number } = $props();

	const status = (d: Dot) => (d.tasted ? 'Tasted' : d.owned ? 'In the cellar, to taste' : 'To taste');

	// One hover card for the mosaic, placed against the window (as RegionStrip's), so a card can't clip it
	let tip = $state<{ dot: Dot; x: number; y: number; below: boolean } | null>(null);
	function show(dot: Dot, e: Event) {
		if (!dot.label) return;
		const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
		const below = r.top < 90;
		tip = { dot, x: Math.min(Math.max(r.left + r.width / 2, 148), innerWidth - 148), y: below ? r.bottom : r.top, below };
	}
</script>

<span class="dots" style:--d="{size}px">
	{#each dots as d, i (i)}
		<svelte:element
			this={d.href ? 'a' : 'span'}
			href={d.href}
			class="dot"
			class:tasted={d.tasted}
			style:--region={regionColor(d.region) ?? FALLBACK_REGION}
			style:--wine={d.color ? typeColor(d.color) : 'transparent'}
			role={d.href ? undefined : 'img'}
			aria-label={d.label ? `${d.label}, ${status(d).toLowerCase()}` : status(d)}
			onmouseenter={(e: Event) => show(d, e)}
			onmouseleave={() => (tip = null)}
			onfocus={(e: Event) => show(d, e)}
			onblur={() => (tip = null)}
		>{#if d.tasted || d.owned}<span class="cork"></span>{/if}</svelte:element>
	{/each}
	{#if tip}
		<span class="tip" class:below={tip.below} style:left="{tip.x}px" style:top="{tip.y}px" role="tooltip">
			<span class="swatch" style:background={regionColor(tip.dot.region) ?? FALLBACK_REGION}></span>
			<span>
				<b>{tip.dot.label}</b>
				{#if tip.dot.note}<span class="line note">{tip.dot.note}</span>{/if}
				<span class="line muted">{[regionLabel(tip.dot.region), status(tip.dot)].filter(Boolean).join(' · ')}</span>
			</span>
		</span>
	{/if}
</span>

<style>
	.dots {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.dot {
		width: var(--d);
		height: var(--d);
		border-radius: 50%;
		box-sizing: border-box;
		border: 2px solid var(--region);
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}
	.dot.tasted {
		background: var(--region);
		border-color: color-mix(in srgb, var(--region) 70%, #000);
	}
	.dot:hover,
	.dot:focus-visible {
		transform: scale(1.35);
		outline: none;
	}
	.dot {
		transition: transform 0.08s;
	}
	.tip {
		position: fixed;
		z-index: 30;
		transform: translate(-50%, calc(-100% - 8px));
		display: flex;
		gap: 8px;
		align-items: flex-start;
		width: max-content;
		max-width: 280px;
		padding: 7px 10px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface);
		color: var(--text);
		box-shadow: var(--shadow);
		font-size: 12px;
		font-weight: 400;
		line-height: 1.35;
		pointer-events: none;
	}
	.tip.below {
		transform: translate(-50%, 8px);
	}
	.line {
		display: block;
	}
	.note {
		font-style: italic;
	}
	.swatch {
		flex: none;
		width: 4px;
		align-self: stretch;
		border-radius: 2px;
	}
	.cork {
		width: calc(var(--d) * 0.36);
		height: calc(var(--d) * 0.36);
		border-radius: 50%;
		background: var(--wine);
	}
</style>
