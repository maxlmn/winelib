<script lang="ts">
	import { onMount } from 'svelte';

	/** Renders long lists in steps: loads the next step when scrolled into view, or on click. */
	let { shown, total, step, onmore }: { shown: number; total: number; step: number; onmore: () => void } = $props();

	let el: HTMLDivElement;
	let io: IntersectionObserver | undefined = $state();

	onMount(() => {
		io = new IntersectionObserver((entries) => entries[0].isIntersecting && onmore(), { rootMargin: '400px' });
		return () => io?.disconnect();
	});

	// Observing afresh reports the current state, so a sentinel still in view after a step loads the next one
	$effect(() => {
		void shown;
		if (!io) return;
		io.observe(el);
		return () => io?.unobserve(el);
	});
</script>

<div class="more" bind:this={el} hidden={shown >= total}>
	<button class="btn" onclick={onmore}>Show {Math.min(step, total - shown)} more</button>
	<span class="muted num">{shown} of {total}</span>
</div>

<style>
	.more {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 16px 0 4px;
		font-size: 13px;
	}
	.more[hidden] {
		display: none;
	}
</style>
