<script module lang="ts">
	/** One pip: a bottle or a tasting, in its region's color */
	export type Pip = {
		region: string | null;
		/** the wine's color (Red, White...): the second track, or the cork in the rack */
		color?: string | null;
		format?: string | null;
		/** the wine, first line of the hover card */
		label: string;
		/** a second line (date, place, storage...) */
		sub?: string;
		href?: string;
		/** handed to onhover, e.g. to highlight the wine in a list */
		key?: number | string;
	};
</script>

<script lang="ts">
	import { barWidth, endScale } from '#lib/format.ts';
	import { regionColor, regionLabel } from '#lib/regions.svelte.ts';
	import { FALLBACK_REGION, typeColor } from '#lib/colors.ts';

	let {
		pips,
		variant = 'tracks',
		height = 14,
		onhover
	}: {
		pips: Pip[];
		/** tracks: a bar per wine in its region's color, its color on a thin track below (timelines, lists);
		 *  rack: bottles seen end-on in a wine rack, the region's color with the wine's as the cork (a cellar) */
		variant?: 'tracks' | 'rack';
		/** the bar's height, or the bottle end's diameter */
		height?: number;
		onhover?: (key: Pip['key'] | null) => void;
	} = $props();

	// The rack's rows, every other one shifted half a bottle as in a real rack, filled to the width. A bottle end's
	// diameter follows its volume (a magnum ~1.4x a 75cl bottle, a half bottle smaller)
	const GAP = 3;
	let width = $state(0);
	const size = (pip: Pip) => Math.round(height * endScale(pip.format ?? null));
	const rows = $derived.by(() => {
		if (variant !== 'rack') return [];
		const room = (width || 600) - (height + GAP) / 2;
		const out: { pip: Pip; i: number; d: number }[][] = [[]];
		let used = 0;
		pips.forEach((pip, i) => {
			const d = size(pip);
			if (used && used + d > room) {
				out.push([]);
				used = 0;
			}
			out[out.length - 1].push({ pip, i, d });
			used += d + GAP;
		});
		return out;
	});

	// One hover card for the strip, over the pip under the pointer (under it near the top of the window). Placed
	// against the window, so a card or a folded list can't clip it
	let tip = $state<{ pip: Pip; x: number; y: number; below: boolean } | null>(null);

	function show(pip: Pip, e: Event) {
		const el = e.currentTarget as HTMLElement;
		const r = el.getBoundingClientRect();
		const below = r.top < 90;
		// Kept inside the window at its edges (the card is up to 280px wide)
		const x = Math.min(Math.max(r.left + r.width / 2, 148), innerWidth - 148);
		tip = { pip, x, y: below ? r.bottom : r.top, below };
		onhover?.(pip.key ?? null);
	}
	function hide() {
		tip = null;
		onhover?.(null);
	}
</script>

{#snippet one(pip: Pip, d?: number)}
	<svelte:element
		this={pip.href ? 'a' : 'span'}
		class="pip"
		href={pip.href}
		style:--d={d ? `${d}px` : null}
		style:--w={Math.min(2, barWidth(pip.format ?? null) / 4)}
		style:--region={regionColor(pip.region) ?? FALLBACK_REGION}
		style:--wine={pip.color ? typeColor(pip.color) : 'transparent'}
		aria-label="{pip.label}{pip.color ? `, ${pip.color}` : ''}{pip.sub ? `, ${pip.sub}` : ''}"
		onmouseenter={(e: Event) => show(pip, e)}
		onmouseleave={hide}
		onfocus={(e: Event) => show(pip, e)}
		onblur={hide}
		role={pip.href ? undefined : 'img'}
	></svelte:element>
{/snippet}

<div class="strip {variant}" style:--h="{height}px" style:--gap="{GAP}px" bind:clientWidth={width}>
	{#if variant === 'rack'}
		{#each rows as row, r (r)}
			<div class="row" class:shifted={r % 2 === 1}>{#each row as x (x.i)}{@render one(x.pip, x.d)}{/each}</div>
		{/each}
	{:else}
		{#each pips as pip, i (i)}{@render one(pip)}{/each}
	{/if}
	{#if tip}
		<div class="tip" class:below={tip.below} style:left="{tip.x}px" style:top="{tip.y}px" role="tooltip">
			<span class="swatch" style:background={regionColor(tip.pip.region) ?? FALLBACK_REGION}></span>
			<div>
				<b>{tip.pip.label}</b>
				{#if tip.pip.color}<span class="type"><span class="dot" style:background={typeColor(tip.pip.color)}></span>{tip.pip.color}</span>{/if}
				<div class="muted">{[regionLabel(tip.pip.region), tip.pip.sub].filter(Boolean).join(' · ')}</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.strip {
		position: relative;
	}
	.pip {
		display: block;
		flex: none;
		position: relative;
		background: var(--region);
		/* a hairline, so pale regions (England's white) still show on a light page */
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--text) 14%, transparent);
		transition: transform 0.08s;
	}
	.pip:hover,
	.pip:focus-visible {
		z-index: 1;
		outline: none;
	}

	/* Tracks: the region's bar, 5px for a 75cl bottle (half bottles thinner, magnums and up twice as wide), and the
	   wine's color on a thin track under it */
	.tracks {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 2px;
	}
	.tracks .pip {
		width: calc(5px * var(--w, 1));
		height: var(--h);
		margin-bottom: 5px;
		border-radius: 1.5px;
		transform-origin: bottom;
	}
	.tracks .pip::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: calc(100% + 2px);
		height: 3px;
		border-radius: 1px;
		background: var(--wine);
	}
	.tracks .pip:hover,
	.tracks .pip:focus-visible {
		transform: scale(1.6, 1.25);
	}

	/* Rack: bottle ends in rows, every other row shifted half a bottle, sized by volume; the wine's color as the
	   cork */
	.rack {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}
	.row {
		display: flex;
		align-items: center;
		gap: var(--gap);
	}
	.row.shifted {
		margin-left: calc((var(--h) + var(--gap)) / 2);
	}
	.rack .pip {
		width: var(--d, var(--h));
		height: var(--d, var(--h));
		border-radius: 50%;
	}
	.rack .pip::after {
		content: '';
		position: absolute;
		inset: 32%;
		border-radius: 50%;
		background: var(--wine);
	}
	.rack .pip:hover,
	.rack .pip:focus-visible {
		transform: scale(1.5);
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
		box-shadow: var(--shadow);
		font-size: 12px;
		line-height: 1.35;
		pointer-events: none;
	}
	.tip.below {
		transform: translate(-50%, 8px);
	}
	.type {
		display: block;
		color: var(--muted);
	}
	.type .dot {
		display: inline-block;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		margin-right: 5px;
	}
	.swatch {
		flex: none;
		width: 4px;
		align-self: stretch;
		border-radius: 2px;
	}
</style>
