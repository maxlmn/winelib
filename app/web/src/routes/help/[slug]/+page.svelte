<script lang="ts">
	/** A Help guide, with the previous and next ones. */
	import Markdown from '#lib/components/Markdown.svelte';
	import { links } from '#lib/links.ts';

	let { data } = $props();
	const g = $derived(data.guide);
</script>

<svelte:head><title>{g.title} · Help · WineLib</title></svelte:head>

<article class="page">
	<a class="back muted small" href={links.help()}>← Help</a>
	<h1>{g.title}</h1>
	{#if g.summary}<p class="lead muted">{g.summary}</p>{/if}

	<div class="card body"><Markdown md={g.body} /></div>

	<nav class="pager">
		{#if g.prev}<a class="card" href={links.help(g.prev.slug)}><span class="muted small">← Previous</span>{g.prev.title}</a>{:else}<span></span>{/if}
		{#if g.next}<a class="card next" href={links.help(g.next.slug)}><span class="muted small">Next →</span>{g.next.title}</a>{/if}
	</nav>
</article>

<style>
	.page {
		max-width: 820px;
	}
	.back {
		display: inline-block;
		margin-bottom: 8px;
		text-decoration: none;
	}
	h1 {
		margin: 0 0 6px;
	}
	.lead {
		margin: 0 0 16px;
		font-size: 15px;
	}
	.body {
		padding: 18px 22px;
	}
	.pager {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 14px;
		margin-top: 16px;
	}
	.pager a {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 12px 16px;
		color: inherit;
		text-decoration: none;
		font-weight: 600;
	}
	.pager a:hover {
		border-color: var(--accent);
	}
	.pager .next {
		text-align: right;
		grid-column: 2;
	}
</style>
