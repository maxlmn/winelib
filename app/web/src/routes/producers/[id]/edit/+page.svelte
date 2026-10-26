<script lang="ts">
	import ProducerEditor from '#lib/components/forms/ProducerEditor.svelte';

	let { data } = $props();
</script>

{#key data.producer.id}
	<ProducerEditor options={data.options} producer={data.producer} />
{/key}
