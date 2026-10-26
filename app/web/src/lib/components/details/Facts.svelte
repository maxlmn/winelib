<script lang="ts" module>
	import type { IconName } from '#lib/components/Icon.svelte';
	import type { Maturity } from '#lib/maturity.ts';

	export interface Fact {
		label: string;
		value: string | number | null | undefined;
		/** internal link, or an external one when it starts with http */
		href?: string | null;
		/** a small icon before the value */
		icon?: IconName;
		/** a colour dot before the value (the wine type's) */
		dot?: string | null;
		/** a drinking-window badge after the value */
		maturity?: Maturity;
	}
</script>

<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import MaturityBadge from '#lib/components/MaturityBadge.svelte';

	let { items }: { items: Fact[] } = $props();

	const shown = $derived(items.filter((f) => f.value !== null && f.value !== undefined && String(f.value).trim() !== ''));
	const external = (href: string) => href.startsWith('http');
</script>

{#if shown.length}
	<dl>
		{#each shown as f (f.label)}
			<dt>{f.label}</dt>
			<dd>
				{#if f.dot}<span class="mark"><span class="dot" style:background={f.dot}></span></span>{/if}
				{#if f.icon}<span class="mark"><Icon name={f.icon} /></span>{/if}
				{#if f.href && external(f.href)}
					<a class="link" href={f.href} target="_blank" rel="noreferrer">{f.value} ↗</a>
				{:else if f.href}
					<a class="link" href={f.href}>{f.value}</a>
				{:else}
					{f.value}
				{/if}
				{#if f.maturity}<span class="after"><MaturityBadge maturity={f.maturity} /></span>{/if}
			</dd>
		{/each}
	</dl>
{/if}

<style>
	dl {
		display: grid;
		grid-template-columns: max-content minmax(0, 1fr);
		gap: 6px 16px;
		margin: 0;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	.link {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.link:hover {
		color: var(--accent);
	}
	/* the icon or the type's dot, in the same 14px box so the values line up */
	.after {
		margin-left: 8px;
	}
	.mark {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 14px;
		height: 14px;
		margin-right: 6px;
		vertical-align: -2px;
		color: var(--muted);
	}
	.mark :global(svg) {
		vertical-align: 0;
	}
	.dot {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		transform: translateY(-1px);
	}
	.link:hover {
		text-decoration: underline;
	}
</style>
