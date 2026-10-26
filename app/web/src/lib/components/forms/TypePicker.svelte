<script lang="ts">
	import { TYPE_COLORS } from '#lib/colors.ts';

	let { value, types, name, onchange }: { value: string; types: string[]; name: string; onchange: (t: string) => void } = $props();
</script>

<div class="types" role="radiogroup" aria-label="Type">
	{#each types as t}
		<label class:on={value === t}>
			<input type="radio" {name} value={t} checked={value === t} onchange={() => onchange(t)} />
			<span class="dot" style:background={TYPE_COLORS[t]}></span>{t}
		</label>
	{/each}
</div>

<style>
	.types {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	label {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 11px;
		border: 1px solid var(--border);
		border-radius: 16px;
		background: var(--surface-2);
		cursor: pointer;
		font-size: 13px;
	}
	label:hover {
		border-color: var(--accent);
	}
	label.on {
		border-color: var(--accent);
		background: var(--accent-soft);
		color: var(--accent);
		font-weight: 600;
	}
	label:focus-within {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}
	input {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}
</style>
