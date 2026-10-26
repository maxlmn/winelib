<script lang="ts">
	/** Calls `onvisible` whenever it scrolls into view of `root`: renders long lists a page at a time. */
	/** `shown`: rows rendered so far; observing again after each page fires again if it is still in view */
	let { root, shown, onvisible }: { root?: HTMLElement; shown: number; onvisible: () => void } = $props();

	let el: HTMLDivElement;

	$effect(() => {
		void shown;
		const io = new IntersectionObserver((entries) => entries.some((e) => e.isIntersecting) && onvisible(), {
			root,
			rootMargin: '400px'
		});
		io.observe(el);
		return () => io.disconnect();
	});
</script>

<div bind:this={el} class="sentinel"></div>

<style>
	.sentinel {
		height: 1px;
	}
</style>
