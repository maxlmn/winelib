<script lang="ts">
	import { regionLabel } from '#lib/regions.svelte.ts';
	import type { Snippet } from 'svelte';
	import { FALLBACK_REGION } from '#lib/colors.ts';
	import Icon from '#lib/components/Icon.svelte';
	import type { IconName } from '#lib/components/Icon.svelte';

	interface Props {
		/** what this page is about: "Producer", "Wine", "Appellation · AOC"... */
		kind: string;
		/** before `kind`: person for a producer, globe for a region... */
		icon?: IconName;
		title: Snippet | string;
		/** region > sub-region > village, the region drawn in its color */
		trail?: (string | null | undefined)[];
		regionColor?: string | null;
		/** makes the trail's first item (the region) a link to its page */
		regionHref?: string | null;
		actions?: Snippet;
		/** right column next to the facts, e.g. a map or the stats */
		aside?: Snippet;
		children?: Snippet;
	}

	let { kind, icon, title, trail = [], regionColor, regionHref = null, actions, aside, children }: Props = $props();

	// The first item is the region when the page has one (regionColor / regionHref): named with its country
	const parts = $derived(
		trail.filter((x): x is string => !!x && !!x.trim()).map((p, i) => (i === 0 && (regionColor !== undefined || regionHref) ? regionLabel(p) : p))
	);
</script>

<header class="card head" style:--region={regionColor ?? FALLBACK_REGION}>
	<div class="top">
		<div class="titles">
			<div class="kind">{#if icon}<Icon name={icon} size={12} />{/if}{kind}</div>
			<h1>{#if typeof title === 'string'}{title}{:else}{@render title()}{/if}</h1>
			{#if parts.length}
				<div class="trail">
					{#each parts as p, i}
						{#if i}<span class="sep">›</span>{/if}{#if i === 0 && regionHref}<a class="region-link" class:region={!!regionColor} href={regionHref}>{p}</a>{:else}<span class:region={i === 0 && regionColor}>{p}</span>{/if}
					{/each}
				</div>
			{/if}
		</div>
		{#if actions}<div class="actions">{@render actions()}</div>{/if}
	</div>
	{#if children || aside}
		<div class="body" class:split={aside && children}>
			{#if children}<div class="main">{@render children()}</div>{/if}
			{#if aside}<div class="aside">{@render aside()}</div>{/if}
		</div>
	{/if}
</header>

<style>
	.head {
		border-top: 4px solid var(--region);
		padding: 18px 20px;
		margin-bottom: 14px;
	}
	.top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px 20px;
		flex-wrap: wrap;
	}
	.titles {
		min-width: 0;
	}
	.kind {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted);
		margin-bottom: 2px;
	}
	h1 {
		font-size: 24px;
		line-height: 1.2;
		overflow-wrap: anywhere;
	}
	.trail {
		margin-top: 4px;
		color: var(--muted);
		display: flex;
		flex-wrap: wrap;
		gap: 0 6px;
	}
	.region {
		color: var(--region);
		font-weight: 600;
	}
	.sep {
		opacity: 0.6;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.body {
		margin-top: 16px;
		display: grid;
		gap: 20px;
	}
	.body.split {
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	}
	.main,
	.aside {
		min-width: 0;
	}
	@media (max-width: 900px) {
		.body.split {
			grid-template-columns: 1fr;
		}
	}
	.region-link:hover {
		text-decoration: underline;
	}
</style>
