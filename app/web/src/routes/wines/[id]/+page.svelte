<script lang="ts">
	import WineContent from '#lib/components/details/WineContent.svelte';

	let { data } = $props();
	const wine = $derived(data.detail);
</script>

<svelte:head><title>{wine.producer.name} {wine.cuvee || wine.appellation?.name || ''} {wine.vintage} · WineLib</title></svelte:head>

{#key wine.id}
	<WineContent {wine} regionColors={data.regionColors} />
{/key}
