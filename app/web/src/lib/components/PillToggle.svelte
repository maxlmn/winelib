<script lang="ts">
	/** A map legend's pill button (the layers, Contours): rounded, its swatch and label inside, muted when off */
	import type { Snippet } from 'svelte';

	interface Props {
		off?: boolean;
		/** aria-pressed for an on/off one (Contours); a three-way one (the layers) says its state in its label */
		pressed?: boolean;
		label?: string;
		title: string;
		onclick: () => void;
		children: Snippet;
	}
	let { off = false, pressed, label, title, onclick, children }: Props = $props();
</script>

<button class="toggle" class:off aria-pressed={pressed} aria-label={label} {title} {onclick}>{@render children()}</button>

<style>
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 9px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
		white-space: nowrap;
	}
	.toggle:hover {
		border-color: var(--accent);
	}
	.toggle.off {
		color: var(--muted);
	}
</style>
