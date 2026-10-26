<script lang="ts">
	import WineEditor from '#lib/components/forms/WineEditor.svelte';

	let { data } = $props();
</script>

{#key data.producer?.id}
	<WineEditor options={data.options} wine={null} producer={data.producer} />
{/key}
