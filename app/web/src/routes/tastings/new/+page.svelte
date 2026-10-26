<script lang="ts">
	import { page } from '$app/state';
	import TastingEditor from '#lib/components/forms/TastingEditor.svelte';

	let { data } = $props();
</script>

{#key page.url.search}
	<TastingEditor options={data.options} tasting={null} prefill={data.prefill} />
{/key}
