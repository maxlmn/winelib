<script lang="ts">
	/** Critics' scores as pills, one per critic: "RP 95 · VI 94" makes two */
	let { scores }: { scores: string | null | undefined } = $props();

	const pills = $derived((scores ?? '').split(' · ').filter(Boolean));
</script>

{#each pills as s (s)}<span class="critic num" title="Critics’ scores">{s}</span>{/each}

<style>
	.critic {
		display: inline-block;
		font-size: 11px;
		font-weight: 600;
		line-height: 16px;
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
		border-radius: 8px;
		padding: 0 6px;
		margin-left: 4px;
		white-space: nowrap;
		vertical-align: 1px;
	}
</style>
