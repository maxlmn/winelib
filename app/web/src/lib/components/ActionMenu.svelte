<script lang="ts">
	import type { Snippet } from 'svelte';

	/** A ⋯ button opening a menu of a page's less used actions (its items: links and buttons with the `menu-item` class,
	 * app.css). An item clicked, a click elsewhere or Escape closes it. Its items stay mounted while it's closed, so an
	 * action running from it (a plug-in's search) keeps its state. */
	let { label = 'More actions', children }: { label?: string; children: Snippet } = $props();

	let open = $state(false);
	let root = $state<HTMLElement>();
	let button = $state<HTMLButtonElement>();
	let panel = $state<HTMLElement>();

	const items = () => [...(panel?.querySelectorAll<HTMLElement>('a, button:not(:disabled)') ?? [])].filter((e) => e.offsetParent !== null);
	// Opened under its button's right edge; where that would run off the screen (the button at the left, on a phone),
	// under its left edge instead
	let alignLeft = $state(false);
	$effect(() => {
		if (!open) return;
		alignLeft = false;
		queueMicrotask(() => {
			const r = panel?.getBoundingClientRect();
			if (r && r.left < 8) alignLeft = true;
			items()[0]?.focus();
		});
	});
	function onkey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') {
			open = false;
			button?.focus();
		} else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
			const list = items();
			if (!list.length) return;
			e.preventDefault();
			const i = list.indexOf(document.activeElement as HTMLElement);
			list[(i + (e.key === 'ArrowDown' ? 1 : -1) + list.length) % list.length].focus();
		}
	}

	function onwindow(e: MouseEvent) {
		if (open && root && !root.contains(e.target as Node)) open = false;
	}
	function onpanel(e: MouseEvent) {
		if ((e.target as HTMLElement).closest('a, button')) open = false;
	}
</script>

<svelte:window onclick={onwindow} onkeydown={onkey} />

<div class="action-menu" bind:this={root}>
	<button class="btn more" bind:this={button} aria-haspopup="menu" aria-expanded={open} title={label} aria-label={label} onclick={() => (open = !open)}>⋯</button>
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions: the items are links and buttons -->
	<div class="panel card" class:left={alignLeft} role="menu" tabindex="-1" hidden={!open} onclick={onpanel} bind:this={panel}>
		{@render children()}
	</div>
</div>

<style>
	.action-menu {
		position: relative;
		display: inline-flex;
	}
	.more {
		justify-content: center;
		width: 32px;
		height: 32px;
		padding: 0 0 6px;
		font-size: 17px;
		line-height: 1;
	}
	.panel {
		position: absolute;
		top: calc(100% + 4px);
		right: 0;
		z-index: 30;
		min-width: 220px;
		padding: 6px;
		display: flex;
		flex-direction: column;
		box-shadow: 0 8px 24px rgb(0 0 0 / 14%);
	}
	.panel[hidden] {
		display: none;
	}
	.panel.left {
		right: auto;
		left: 0;
	}
	/* never wider than the screen */
	.panel {
		max-width: calc(100vw - 16px);
	}
</style>
