<script lang="ts">
	import BottleEditor from '#lib/components/forms/BottleEditor.svelte';

	let { data } = $props();
</script>

{#key data.wine?.id}
	<BottleEditor options={data.options} bottle={null} wine={data.wine} />
{/key}
