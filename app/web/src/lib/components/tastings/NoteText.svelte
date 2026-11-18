<script lang="ts">
	import { noteHtml } from '#lib/notes.ts';

	/** A note shown as written: its Markdown (headings, lists, emphasis, links), compact. */
	let { md }: { md: string } = $props();
	const html = $derived(noteHtml(md));
</script>

<div class="note-text">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html html}
</div>

<style>
	.note-text :global(:first-child) {
		margin-top: 0;
	}
	.note-text :global(:last-child) {
		margin-bottom: 0;
	}
	.note-text :global(h1),
	.note-text :global(h2),
	.note-text :global(h3),
	.note-text :global(h4) {
		font-size: 13px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted);
		margin: 12px 0 4px;
	}
	.note-text :global(p) {
		margin: 0 0 8px;
	}
	.note-text :global(ul),
	.note-text :global(ol) {
		margin: 0 0 8px;
		padding-left: 18px;
	}
	.note-text :global(li) {
		margin: 1px 0;
	}
	.note-text :global(table) {
		display: block;
		overflow-x: auto;
		border-collapse: collapse;
		font-size: 13px;
		margin: 4px 0 8px;
	}
	.note-text :global(th),
	.note-text :global(td) {
		text-align: left;
		padding: 3px 8px;
		border-bottom: 1px solid var(--border);
	}
	.note-text :global(a) {
		color: var(--link);
	}
	.note-text :global(hr) {
		border: none;
		border-top: 1px solid var(--border);
		margin: 10px 0;
	}
</style>
