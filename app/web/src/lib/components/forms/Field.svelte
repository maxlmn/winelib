<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		label: string;
		/** id of the control, so the label points at it */
		for?: string;
		hint?: string;
		error?: string;
		required?: boolean;
		span?: boolean;
		children: Snippet;
	}

	let { label, for: id, hint, error, required = false, span = false, children }: Props = $props();
</script>

<div class="field" class:span>
	<label for={id}>{label}{#if required}<span class="req" aria-hidden="true"> *</span>{/if}</label>
	{@render children()}
	{#if error}
		<div class="error" role="alert">{error}</div>
	{:else if hint}
		<div class="hint muted">{hint}</div>
	{/if}
</div>

<style>
	.field {
		display: flex;
		flex-direction: column;
		gap: 5px;
		min-width: 0;
	}
	label {
		font-size: 12px;
		font-weight: 600;
		color: var(--muted);
	}
	.req {
		color: var(--accent);
	}
	.hint,
	.error {
		font-size: 12px;
	}
	.error {
		color: var(--down);
	}
</style>
