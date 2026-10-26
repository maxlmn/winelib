<script lang="ts">
	let { n }: { n: number } = $props();
</script>

{#if n > 0}<span class="stars" title="{n} Michelin star{n === 1 ? '' : 's'}">{'★'.repeat(n)}</span>{/if}

<style>
	.stars {
		color: var(--gold);
		letter-spacing: 1px;
	}
</style>
