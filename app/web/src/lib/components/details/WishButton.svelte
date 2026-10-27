<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import { addWish, type WishItem } from '#lib/api/wishlist.ts';
	import { links } from '#lib/links.ts';

	/** The wine page's Wishlist button: adds the wine; once on the list, a link to it */
	let { wineId, item }: { wineId: number; item: WishItem | null } = $props();

	let added = $state<WishItem | null>(null);
	let busy = $state(false);
	let failed = $state('');
	const on = $derived(added ?? item);

	async function add() {
		busy = true;
		failed = '';
		try {
			added = await addWish({ wine_id: wineId, any_vintage: false, bottle_size: null, target_price: null, currency: null, note: null, url: null });
		} catch (e) {
			failed = e instanceof Error ? e.message : 'Couldn’t add it';
		} finally {
			busy = false;
		}
	}
</script>

{#if on}
	<a class="btn wished" href={links.wishlist()} title="On your wishlist: see it there"><Icon name="star" size={13} /> On your wishlist</a>
{:else}
	<button class="btn" onclick={add} disabled={busy} title={failed || 'Add this wine to your wishlist'}><Icon name="star" size={13} /> Wishlist</button>
{/if}

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.wished {
		color: var(--accent);
		border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
	}
	.wished :global(.icon) {
		fill: currentColor;
	}
</style>
