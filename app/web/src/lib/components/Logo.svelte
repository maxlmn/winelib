<script lang="ts">
	/** WineLib's mark, a wine glass in a map pin, in the palette's colours: the pin the accent, the glass what reads on
	 * it (--on-accent). The same drawing as the favicon and the icons (scripts/brand.mjs draws those). */
	let { size = 22 }: { size?: number } = $props();
</script>

<svg class="logo" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
	<path d="M32 3a21 21 0 0 1 21 21c0 15-21 37-21 37S11 39 11 24A21 21 0 0 1 32 3z" fill="var(--accent)" />
	<path d="M24 13h16c0 9-2.6 13.6-8 14.3-5.4-.7-8-5.3-8-14.3z" fill="none" stroke="var(--on-accent)" stroke-width="2.6" stroke-linejoin="round" />
	<path d="M24.6 19h14.8c-.7 5-3.2 7.6-7.4 8.2-4.2-.6-6.7-3.2-7.4-8.2z" fill="var(--on-accent)" />
	<path d="M32 27.3V35M27.5 36h9" fill="none" stroke="var(--on-accent)" stroke-width="2.6" stroke-linecap="round" />
</svg>

<style>
	.logo {
		flex: none;
		display: block;
	}
</style>
