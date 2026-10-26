<script lang="ts">
	import type { Snippet } from 'svelte';

	let { label, value, help, sub }: { label: string; value: string | number; help?: string; sub?: Snippet } = $props();
</script>

<div class="kpi card" title={help}>
	<div class="label">{label}{#if help}<span class="help">?</span>{/if}</div>
	<div class="value num">{value}</div>
	{#if sub}<div class="sub muted">{@render sub()}</div>{/if}
</div>

<style>
	.kpi {
		padding: 14px 16px;
	}
	.label {
		font-size: 12px;
		color: var(--muted);
		display: flex;
		align-items: center;
		gap: 5px;
	}
	.help {
		display: inline-grid;
		place-items: center;
		width: 13px;
		height: 13px;
		border-radius: 50%;
		border: 1px solid var(--border);
		font-size: 9px;
		cursor: help;
	}
	.value {
		font-size: 22px;
		font-weight: 650;
		letter-spacing: -0.01em;
		margin: 2px 0;
	}
	.sub {
		font-size: 12px;
	}
</style>
