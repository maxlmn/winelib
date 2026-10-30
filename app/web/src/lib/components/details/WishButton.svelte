<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { addEntry, listsOf, wishlistId } from '#lib/api/lists.ts';
	import { links } from '#lib/links.ts';

	/** The wine page's wishlist item (its ⋯ menu): adds the wine (this vintage) to the wishlist, one of the lists; once
	 * there, a link to it */
	let { wineId }: { wineId: number } = $props();

	let listId = $state<number | null>(null);
	let busy = $state(false);
	let failed = $state('');

	$effect(() => {
		const id = wineId;
		listId = null;
		listsOf(fetch, { wine_id: id })
			.then((on) => (listId = on.find((m) => m.is_wishlist && m.as !== 'producer')?.id ?? null))
			.catch(() => {});
	});

	async function add() {
		busy = true;
		failed = '';
		try {
			const id = await wishlistId();
			await addEntry(id, { kind: 'wine', wine_id: wineId });
			listId = id;
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Couldn’t add it';
		} finally {
			busy = false;
		}
	}
</script>

{#if listId}
	<a class="menu-item wished" role="menuitem" href={links.list(listId)}><Icon name="star" size={15} />On your wishlist: see it</a>
{:else}
	<button class="menu-item" role="menuitem" onclick={add} disabled={busy} title={failed || undefined}><Icon name="star" size={15} />{failed || 'Add to your wishlist'}</button>
{/if}

<style>
	.wished {
		color: var(--accent);
		border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
	}
	.wished :global(.icon) {
		fill: currentColor;
	}
</style>
