<script lang="ts">
	import VisitEditor from '#lib/components/forms/VisitEditor.svelte';

	let { data } = $props();
</script>

{#key data.visit.id}
	<VisitEditor options={data.options} visit={data.visit} place={null} />
{/key}
