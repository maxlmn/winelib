<script lang="ts">
	/** Help: the guides, one card each. */
	import { links } from '#lib/links.ts';

	let { data } = $props();
</script>

<svelte:head><title>Help · WineLib</title></svelte:head>

<div class="page">
	<div class="head">
		<h1>Help</h1>
		<p class="muted">Short guides to what WineLib does. Where the data comes from: <a href={links.about()}>About the data</a>.</p>
	</div>

	<div class="grid">
		{#each data.guides as g, i (g.slug)}
			<a class="card guide" href={links.help(g.slug)}>
				<span class="n muted num">{i + 1}</span>
				<h2>{g.title}</h2>
				<p class="muted">{g.summary}</p>
			</a>
		{/each}
	</div>
</div>

<style>
	.page {
		max-width: 1100px;
	}
	.head {
		margin-bottom: 18px;
	}
	.head h1 {
		margin-bottom: 4px;
	}
	.head p {
		margin: 0;
	}
	.head a {
		color: var(--link);
		text-decoration: var(--link-decoration, none);
	}
	.head a:hover {
		color: var(--accent);
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(280px, 100%), 1fr));
		gap: 14px;
	}
	.guide {
		display: block;
		padding: 16px 18px;
		color: inherit;
		text-decoration: none;
		transition: border-color 0.15s;
	}
	.guide:hover {
		border-color: var(--accent);
	}
	.guide h2 {
		margin: 4px 0 6px;
		font-size: 16px;
	}
	.guide p {
		margin: 0;
		font-size: 13px;
		line-height: 1.5;
	}
	.n {
		font-size: 12px;
	}
</style>
