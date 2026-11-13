<script lang="ts">
	/** WineLib's mark: a black wine glass of bordeaux in a white map pin, the same in every palette and theme (white and
	 * black read on any ground). The same drawing as the favicon and the icons (scripts/brand.mjs draws those). */
	let { size = 22 }: { size?: number } = $props();
</script>

<svg class="logo" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
	<path d="M32 3a21 21 0 0 1 21 21c0 15-21 37-21 37S11 39 11 24A21 21 0 0 1 32 3z" fill="#fff" stroke="#1c1719" stroke-width="2.6" stroke-linejoin="round" />
	<path d="M24 13h16c0 9-2.6 13.6-8 14.3-5.4-.7-8-5.3-8-14.3z" fill="none" stroke="#1c1719" stroke-width="2.6" stroke-linejoin="round" />
	<path d="M24.6 19h14.8c-.7 5-3.2 7.6-7.4 8.2-4.2-.6-6.7-3.2-7.4-8.2z" fill="#8e2443" />
	<path d="M32 27.3V35M27.5 36h9" fill="none" stroke="#1c1719" stroke-width="2.6" stroke-linecap="round" />
</svg>

<style>
	.logo {
		flex: none;
		display: block;
	}
</style>
