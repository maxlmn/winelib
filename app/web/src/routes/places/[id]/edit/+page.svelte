<script lang="ts">
	import PlaceEditor from '#lib/components/forms/PlaceEditor.svelte';

	let { data } = $props();
</script>

{#key data.place.id}
	<PlaceEditor options={data.options} place={data.place} />
{/key}
