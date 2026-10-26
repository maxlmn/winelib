<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		aside?: Snippet;
		/** collapsible sections show `summary` while closed */
		collapsible?: boolean;
		open?: boolean;
		summary?: string;
		children: Snippet;
	}

	let { title, aside, collapsible = false, open = $bindable(true), summary, children }: Props = $props();
</script>

<section class="card" class:closed={collapsible && !open}>
	<header>
		{#if collapsible}
			<button type="button" class="toggle" aria-expanded={open} onclick={() => (open = !open)}>
				<span class="chev" class:open>▸</span>
				<h2>{title}</h2>
				{#if !open && summary}<span class="summary muted">{summary}</span>{/if}
			</button>
		{:else}
			<h2>{title}</h2>
		{/if}
		{#if aside}{@render aside()}{/if}
	</header>
	{#if !collapsible || open}{@render children()}{/if}
</section>

<style>
	section {
		padding: 16px 18px 18px;
	}
	section.closed {
		padding-bottom: 16px;
	}
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		margin-bottom: 14px;
	}
	.closed header {
		margin-bottom: 0;
	}
	h2 {
		margin: 0;
		font-size: 14px;
		font-weight: 650;
	}
	.toggle {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
		padding: 0;
		border: none;
		background: none;
		cursor: pointer;
		text-align: left;
	}
	.chev {
		color: var(--muted);
		font-size: 11px;
		transition: transform 0.15s;
	}
	.chev.open {
		transform: rotate(90deg);
	}
	.summary {
		font-size: 13px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
