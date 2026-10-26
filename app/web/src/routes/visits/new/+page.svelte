<script lang="ts">
	import VisitEditor from '#lib/components/forms/VisitEditor.svelte';

	let { data } = $props();
</script>

{#key data.place?.id}
	<VisitEditor options={data.options} visit={null} place={data.place} />
{/key}
