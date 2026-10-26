<script lang="ts">
	import PlaceEditor from '#lib/components/forms/PlaceEditor.svelte';

	let { data } = $props();
</script>

<PlaceEditor options={data.options} place={null} />
