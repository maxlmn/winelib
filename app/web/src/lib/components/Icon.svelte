<script lang="ts" module>
	export const ICONS = ['person', 'globe', 'map', 'grape', 'home', 'home-solid', 'grid', 'bottle', 'glass', 'chart', 'calendar', 'pin', 'help', 'sliders'] as const;
	export type IconName = (typeof ICONS)[number];
	/** for fields holding either a text glyph ('✦') or one of these icons */
	export const isIcon = (s: string): s is IconName => (ICONS as readonly string[]).includes(s);
</script>

<script lang="ts">
	/** Small line icons (14px, the text's colour) */
	let { name, size = 14 }: { name: IconName; size?: number } = $props();
</script>

<svg class="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
	stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
	{#if name === 'person'}
		<circle cx="12" cy="8" r="4" />
		<path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" />
	{:else if name === 'globe'}
		<circle cx="12" cy="12" r="9" />
		<path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z" />
	{:else if name === 'map'}
		<path d="M9 4 3 6.5v13.5l6-2.5 6 2.5 6-2.5V4l-6 2.5L9 4z" />
		<path d="M9 4v13.5M15 6.5V20" />
	{:else if name === 'grape'}
		<path d="M12 6V3m0 3c1-1.6 2.6-2.4 4.5-2.3" />
		<circle cx="9" cy="9.5" r="2.4" />
		<circle cx="15" cy="9.5" r="2.4" />
		<circle cx="12" cy="13.5" r="2.4" />
		<circle cx="7.6" cy="14.2" r="2.2" />
		<circle cx="16.4" cy="14.2" r="2.2" />
		<circle cx="12" cy="18.6" r="2.3" />
	{:else if name === 'home'}
		<path d="M3 11 12 4l9 7" />
		<path d="M5.5 9.5V20h13V9.5" />
		<path d="M10 20v-5h4v5" />
	{:else if name === 'grid'}
		<rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
		<rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
		<rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
		<rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
	{:else if name === 'bottle'}
		<path d="M10 2.5h4M10.5 2.5v4.3c0 .9-.4 1.6-1.1 2.2C8.5 9.7 8 10.7 8 11.9V20a1.5 1.5 0 0 0 1.5 1.5h5A1.5 1.5 0 0 0 16 20v-8.1c0-1.2-.5-2.2-1.4-2.9-.7-.6-1.1-1.3-1.1-2.2V2.5" />
		<path d="M8 14h8" />
	{:else if name === 'glass'}
		<path d="M7 3h10l-.5 5.3a4.5 4.5 0 0 1-9 0L7 3z" />
		<path d="M12 12.8V20M8.5 21h7" />
	{:else if name === 'chart'}
		<path d="M4 20h16M7 20v-6M12 20V7M17 20v-9" />
	{:else if name === 'calendar'}
		<rect x="3.5" y="4.5" width="17" height="16" rx="2" />
		<path d="M3.5 9.5h17M8 2.5v4M16 2.5v4" />
	{:else if name === 'pin'}
		<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" />
		<circle cx="12" cy="10" r="2.3" />
	{:else if name === 'help'}
		<circle cx="12" cy="12" r="9" />
		<path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.1-2.4 3.8" />
		<path d="M12 17.2v.1" />
	{:else if name === 'sliders'}
		<path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
		<circle cx="15" cy="7" r="2" />
		<circle cx="9" cy="17" r="2" />
	{:else if name === 'home-solid'}
		<path d="M12 3.2 2.4 10.7a1 1 0 0 0 1.2 1.6l.9-.7V20a1 1 0 0 0 1 1H10v-5.5h4V21h4.5a1 1 0 0 0 1-1v-8.4l.9.7a1 1 0 0 0 1.2-1.6L12 3.2z"
			fill="currentColor" stroke="none" />
	{/if}
</svg>

<style>
	.icon {
		flex: none;
		vertical-align: -2px;
	}
</style>
