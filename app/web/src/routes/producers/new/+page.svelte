<script lang="ts">
	import ProducerEditor from '#lib/components/forms/ProducerEditor.svelte';

	let { data } = $props();
</script>

<ProducerEditor options={data.options} producer={null} />
