<script lang="ts">
	import AppellationEditor from '#lib/components/forms/AppellationEditor.svelte';

	let { data } = $props();
</script>

{#key data.appellation.id}
	<AppellationEditor options={data.options} appellation={data.appellation} />
{/key}
