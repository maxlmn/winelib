<script lang="ts">
	import RegionName from '#lib/components/RegionName.svelte';
	import type { Snippet } from 'svelte';
	import { TYPE_COLORS } from '#lib/colors.ts';
	import { vintageLabel } from '#lib/api/forms.ts';
	import type { WineSummary } from '#lib/api/forms.ts';

	/** One wine, as a compact read-only line (picked wine, locked wine of a tasting...). */
	/** below: more lines under the details (a plug-in import's review and notes) */
	let { wine, extra, actions, below }: { wine: WineSummary; extra?: string; actions?: Snippet; below?: Snippet } = $props();

	const details = $derived([wine.appellation, wine.varietal].filter(Boolean).join(' · '));
</script>

<div class="wine">
	<span class="dot" style:background={TYPE_COLORS[wine.type ?? ''] ?? 'var(--muted)'}></span>
	<div class="text">
		<div class="title">
			<b>{wine.producer}</b>
			{#if wine.cuvee}<span>{wine.cuvee}</span>{/if}
			{#if wine.vintage}<span class="num">{vintageLabel(wine)}</span>{/if}
		</div>
		<div class="muted small">
			{details}{#if wine.region}{details ? ' · ' : ''}<RegionName name={wine.region} />{/if}{#if extra}{details || wine.region ? ' · ' : ''}{extra}{/if}
		</div>
		{#if below}{@render below()}{/if}
	</div>
	{#if actions}<div class="actions">{@render actions()}</div>{/if}
</div>

<style>
	.wine {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 12px;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--surface-2);
	}
	.text {
		flex: 1;
		min-width: 0;
	}
	.title {
		display: flex;
		flex-wrap: wrap;
		gap: 0 6px;
	}
	.small {
		font-size: 12px;
	}
	.actions {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
		justify-content: flex-end;
	}
</style>
