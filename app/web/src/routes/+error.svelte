<script lang="ts">
	import { page } from '$app/state';
	import { links } from '#lib/links.ts';
</script>

<svelte:head><title>{page.status} · WineLib</title></svelte:head>

<div class="err card">
	<div class="code">{page.status}</div>
	<p>{page.status === 404 ? 'This page doesn’t exist.' : (page.error?.message ?? 'Something went wrong.')}</p>
	<a class="btn" href={links.cellar()}>Back to the cellar</a>
</div>

<style>
	.err {
		max-width: 420px;
		margin: 80px auto;
		padding: 28px;
		text-align: center;
	}
	.code {
		font-size: 42px;
		font-weight: 700;
		color: var(--accent);
	}
	p {
		color: var(--muted);
	}
</style>
