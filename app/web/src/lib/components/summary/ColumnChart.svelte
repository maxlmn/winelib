<script lang="ts" module>
	export interface Column {
		label: string;
		count: number;
		color?: string;
		href?: string;
		/** stacked from the bottom, each in its color (a vintage by region) */
		segments?: { label: string; count: number; color: string }[];
	}
</script>

<script lang="ts">
	/** Vertical bars on a light grid, with the value on hover. */
	interface Props {
		columns: Column[];
		unit: string;
		color?: string;
		height?: number;
	}

	let { columns, unit, color = 'var(--accent)', height = 200 }: Props = $props();

	const peak = $derived(Math.max(1, ...columns.map((c) => c.count)));
	// ~4 gridlines on round numbers
	const ticks = $derived.by(() => {
		const raw = peak / 4;
		const mag = 10 ** Math.floor(Math.log10(raw));
		const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
		return Array.from({ length: Math.floor(peak / step) }, (_, i) => (i + 1) * step);
	});
	const top = $derived(Math.max(peak, ticks.at(-1) ?? 0));
	const narrow = $derived(columns.length > 12);
	const minWidth = $derived(`${columns.length * ((narrow ? 12 : 28) + 2)}px`);
</script>

<div class="chart" class:narrow>
	<div class="plot" style:height="{height}px" style:min-width={minWidth}>
		{#each ticks as t}
			<div class="grid" style:bottom="{(t / top) * 100}%"><span class="tick num">{t}</span></div>
		{/each}
		<div class="cols" style:grid-template-columns="repeat({columns.length}, minmax({narrow ? 12 : 28}px, 1fr))">
			{#each columns as c (c.label)}
				<svelte:element
					this={c.href ? 'a' : 'div'}
					href={c.href}
					class="col"
					title="{c.label}: {c.count} {unit}"
					role={c.href ? undefined : 'img'}
					aria-label="{c.label}: {c.count} {unit}"
				>
					<span class="tip num">{c.count}</span>
					<span class="bar" class:stacked={c.segments} style:height="{(c.count / top) * 100}%" style:background={c.segments ? null : (c.color ?? color)}>
						{#each c.segments ?? [] as s (s.label)}<span class="part" style:flex-grow={s.count} style:background={s.color} title="{s.label}: {s.count} {unit}"></span>{/each}
					</span>
				</svelte:element>
			{/each}
		</div>
	</div>
	<div class="labels" style:min-width={minWidth} style:grid-template-columns="repeat({columns.length}, minmax({narrow ? 12 : 28}px, 1fr))">
		{#each columns as c (c.label)}<span class="lbl num">{c.label}</span>{/each}
	</div>
</div>

<style>
	.chart {
		overflow-x: auto;
		padding: 16px 0 2px 34px;
	}
	.plot {
		position: relative;
		border-bottom: 1px solid var(--border);
	}
	.grid {
		position: absolute;
		left: 0;
		right: 0;
		border-top: 1px dashed color-mix(in srgb, var(--border) 80%, transparent);
	}
	.tick {
		position: absolute;
		right: calc(100% + 6px);
		top: -8px;
		font-size: 10px;
		color: var(--muted);
	}
	.cols,
	.labels {
		display: grid;
		gap: 2px;
	}
	.cols {
		position: absolute;
		inset: 0;
	}
	.col {
		position: relative;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		align-items: center;
		height: 100%;
	}
	.bar {
		width: min(100%, 44px);
		min-height: 2px;
		border-radius: 4px 4px 0 0;
		box-shadow: inset 0 0 0 1px #00000024;
	}
	.bar.stacked {
		display: flex;
		flex-direction: column-reverse;
		gap: 1px;
		overflow: hidden;
		box-shadow: none;
	}
	.part {
		flex-basis: 0;
		min-height: 1px;
	}
	.col:hover .bar {
		filter: brightness(1.08) saturate(1.1);
	}
	.tip {
		visibility: hidden;
		font-size: 11px;
		font-weight: 600;
		padding-bottom: 2px;
		white-space: nowrap;
	}
	.col:hover .tip {
		visibility: visible;
	}
	.lbl {
		font-size: 11px;
		color: var(--muted);
		text-align: center;
		padding-top: 4px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.narrow .lbl {
		writing-mode: vertical-rl;
		transform: rotate(180deg);
		justify-self: center;
		padding: 0 0 4px;
		font-size: 10px;
	}
</style>
