<script lang="ts">
	import VineyardEditor from '#lib/components/forms/VineyardEditor.svelte';

	let { data } = $props();
</script>

{#key data.vineyard.id}
	<VineyardEditor options={data.options} vineyard={data.vineyard} />
{/key}
