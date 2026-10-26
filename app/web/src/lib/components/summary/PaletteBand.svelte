<script lang="ts" module>
	export interface Segment {
		label: string;
		count: number;
		color: string;
		href?: string;
	}
</script>

<script lang="ts">
	/** One band split into colored segments, as wide as their counts: where the wines come from at a glance. */
	let { segments, unit, height = 22 }: { segments: Segment[]; unit: string; height?: number } = $props();

	const total = $derived(segments.reduce((n, s) => n + s.count, 0));
</script>

<div class="band" style:height="{height}px">
	{#each segments as s (s.label)}
		<svelte:element
			this={s.href ? 'a' : 'span'}
			href={s.href}
			class="seg-part"
			style:flex-grow={s.count}
			style:background={s.color}
			title="{s.label}: {s.count} {unit} ({total ? ((s.count / total) * 100).toFixed(1) : 0}%)"
			aria-label="{s.label}: {s.count} {unit}"
			role={s.href ? undefined : 'img'}
		></svelte:element>
	{/each}
</div>

<style>
	.band {
		display: flex;
		gap: 2px;
		border-radius: 6px;
		overflow: hidden;
	}
	.seg-part {
		flex-basis: 0;
		min-width: 3px;
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--text) 10%, transparent);
		transition: filter 0.1s;
	}
	.seg-part:hover {
		filter: brightness(1.08) saturate(1.15);
	}
</style>
