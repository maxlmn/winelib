<script lang="ts">
	import BottleEditor from '#lib/components/forms/BottleEditor.svelte';

	let { data } = $props();
</script>

{#key data.bottle.id}
	<BottleEditor options={data.options} bottle={data.bottle} wine={null} />
{/key}
