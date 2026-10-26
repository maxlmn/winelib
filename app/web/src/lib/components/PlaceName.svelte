<script lang="ts">
	/** A place's name, with a house before it for a home: solid for yours (Home), outlined for a friend's (who it is,
	 * the name, after) */
	import Icon from '#lib/components/Icon.svelte';
	import { isFriends, isHome } from '#lib/places.ts';

	let { name, type }: { name: string; type?: string | null } = $props();
</script>

{#if isHome(type)}<span class="home" title="Your home"><Icon name="home-solid" size={13} /></span>{:else if isFriends(type)}<span
		class="home" title="At {name}'s"><Icon name="home" size={13} /></span>{/if}{name}

<style>
	.home {
		margin-right: 4px;
		opacity: 0.85;
	}
</style>
