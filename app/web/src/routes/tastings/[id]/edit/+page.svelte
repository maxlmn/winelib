<script lang="ts">
	import TastingEditor from '#lib/components/forms/TastingEditor.svelte';

	let { data } = $props();

	const noPrefill = { bottle: null, wine: null, place: null, date: null };
</script>

{#key data.tasting.id}
	<TastingEditor options={data.options} tasting={data.tasting} prefill={noPrefill} />
{/key}
