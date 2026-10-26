<script lang="ts">
	/** A % change: ▲ in the up colour, ▼ in the down colour, a grey – when it rounds to 0; nothing without a value. */
	let { value, digits = 0 }: { value: number | null | undefined; digits?: number } = $props();
	const shown = $derived(value == null ? null : Math.abs(value).toFixed(digits));
	const flat = $derived(shown !== null && Number(shown) === 0);
</script>

{#if value != null}
	{#if flat}<span class="flat">–</span>{:else}<span class:up={value > 0} class:down={value < 0}>{value > 0 ? '▲' : '▼'} {shown}%</span>{/if}
{/if}

<style>
	.up {
		color: var(--up);
	}
	.down {
		color: var(--down);
	}
	.flat {
		color: var(--muted);
	}
</style>
