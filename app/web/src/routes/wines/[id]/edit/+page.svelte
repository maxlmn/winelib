<script lang="ts">
	import WineEditor from '#lib/components/forms/WineEditor.svelte';

	let { data } = $props();
</script>

{#key data.wine.id}
	<WineEditor options={data.options} wine={data.wine} producer={null} />
{/key}
