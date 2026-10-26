<script lang="ts">
	/** Our own Markdown (app/api/data/docs/: About the data, the Help guides), rendered as it is; links to other sites
	 * open in a new tab. */
	import { marked } from 'marked';

	let { md }: { md: string } = $props();
	const html = $derived(
		(marked.parse(md, { async: false }) as string).replace(/<a href="(https?:[^"]+)"/g, '<a href="$1" target="_blank" rel="noreferrer"')
	);
</script>

<div class="md">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html html}
</div>

<style>
	.md {
		font-size: 14px;
		line-height: 1.6;
	}
	.md :global(h2) {
		font-size: 15px;
		margin: 20px 0 8px;
	}
	.md :global(h2:first-child) {
		margin-top: 0;
	}
	.md :global(h3) {
		font-size: 14px;
		margin: 16px 0 6px;
	}
	.md :global(p) {
		margin: 0 0 10px;
	}
	.md :global(table) {
		display: block;
		overflow-x: auto;
		border-collapse: collapse;
		font-size: 13px;
		margin: 6px 0 12px;
	}
	.md :global(th),
	.md :global(td) {
		text-align: left;
		vertical-align: top;
		padding: 6px 10px;
		border-bottom: 1px solid var(--border);
	}
	.md :global(th) {
		color: var(--muted);
		font-weight: 600;
	}
	.md :global(ul),
	.md :global(ol) {
		padding-left: 20px;
		margin: 0 0 10px;
	}
	.md :global(li) {
		margin: 4px 0;
	}
	.md :global(a) {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.md :global(a:hover) {
		color: var(--accent);
	}
	.md :global(code) {
		font-size: 12px;
		background: var(--surface-2);
		padding: 1px 5px;
		border-radius: 4px;
	}
</style>
